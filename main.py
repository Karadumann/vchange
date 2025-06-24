import pyaudio
import numpy as np
from pedalboard import Pedalboard, PitchShift, Reverb, Chorus, Delay, HighpassFilter, LowpassFilter
import threading
import customtkinter as ctk
import json
import os

PRESETS_FILE = "presets.json"

class VoiceChanger:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream_active = False
        self.thread = None
        self.volume_callback = None

        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        
        self.input_device_index = self.p.get_default_input_device_info()['index']
        self.output_device_index = self.p.get_default_output_device_info()['index']
        
        self.board = Pedalboard([])
        self.pitch_shifter = PitchShift(semitones=0)
        self.high_pass_filter = HighpassFilter(cutoff_frequency_hz=0)
        self.low_pass_filter = LowpassFilter(cutoff_frequency_hz=22000)
        self.reverb = Reverb(room_size=0.0)
        self.chorus = Chorus(rate_hz=1.0)
        self.delay = Delay(delay_seconds=0.5, feedback=0.3)
        
        self.update_effects()

    def update_effects(self, pitch=0.0, high_pass=0.0, low_pass=22000.0,
                       reverb_on=False, room_size=0.0, chorus_on=False, delay_on=False):
        
        self.pitch_shifter.semitones = pitch
        self.high_pass_filter.cutoff_frequency_hz = high_pass
        self.low_pass_filter.cutoff_frequency_hz = low_pass
        self.reverb.room_size = room_size

        new_board = []
        if high_pass > 0:
            new_board.append(self.high_pass_filter)
        if low_pass < 22000:
            new_board.append(self.low_pass_filter)
        if pitch != 0:
            new_board.append(self.pitch_shifter)
        if reverb_on:
            new_board.append(self.reverb)
        if chorus_on:
            new_board.append(self.chorus)
        if delay_on:
            new_board.append(self.delay)

        self.board.plugins = new_board

    def set_input_device(self, device_name):
        if isinstance(device_name, str):
            devices = self.get_devices()
            input_devices = {dev['name']: dev['index'] for dev in devices if dev['maxInputChannels'] > 0}
            index = input_devices.get(device_name)
            if index is not None:
                self.input_device_index = index
        else:
            self.input_device_index = device_name

    def set_output_device(self, index):
        self.output_device_index = index
        
    def get_devices(self):
        devices = []
        for i in range(self.p.get_device_count()):
            devices.append(self.p.get_device_info_by_index(i))
        return devices

    def start(self):
        if not self.stream_active:
            self.stream_active = True
            self.thread = threading.Thread(target=self._process_audio)
            self.thread.daemon = True
            self.thread.start()

    def stop(self):
        if self.stream_active:
            self.stream_active = False
            if self.thread:
                self.thread.join(timeout=1.0)

    def _process_audio(self):
        try:
            stream_in = self.p.open(format=self.FORMAT,
                                    channels=self.CHANNELS,
                                    rate=self.RATE,
                                    input=True,
                                    frames_per_buffer=self.CHUNK,
                                    input_device_index=self.input_device_index)

            stream_out = self.p.open(format=self.FORMAT,
                                     channels=self.CHANNELS,
                                     rate=self.RATE,
                                     output=True,
                                     frames_per_buffer=self.CHUNK,
                                     output_device_index=self.output_device_index)
        except OSError:
            self.stream_active = False
            if self.volume_callback: self.volume_callback(0)
            return

        while self.stream_active:
            try:
                data_in = stream_in.read(self.CHUNK, exception_on_overflow=False)
                audio_data_int16 = np.frombuffer(data_in, dtype=np.int16)
                
                if self.volume_callback:
                    rms = np.sqrt(np.mean(audio_data_int16.astype(np.float64)**2))
                    self.volume_callback(rms)

                audio_data_float32 = audio_data_int16.astype(np.float32) / 32767.0
                
                if len(self.board.plugins) > 0:
                    processed_audio = self.board(audio_data_float32, self.RATE)
                    processed_audio_int16 = (processed_audio * 32767.0).astype(np.int16)
                    data_out = processed_audio_int16.tobytes()
                else:
                    data_out = data_in

                stream_out.write(data_out)
            except IOError:
                self.stream_active = False

        if self.volume_callback: self.volume_callback(0)
        stream_in.stop_stream()
        stream_in.close()
        stream_out.stop_stream()
        stream_out.close()
        
    def __del__(self):
        if self.stream_active:
            self.stop()
        self.p.terminate()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.voice_changer = VoiceChanger()
        self.voice_changer.volume_callback = self.update_volume_meter
        self.presets = {}
        self.selected_output_device_index = None
        self.default_presets = {
            "Normal": {"pitch": 0, "high_pass": 0, "low_pass": 22000, "reverb_on": False, "room_size": 0, "chorus_on": False, "delay_on": False},
            "Lower Timbre": {"pitch": -2, "high_pass": 80, "low_pass": 8000, "reverb_on": False, "room_size": 0, "chorus_on": False, "delay_on": False},
            "Higher Timbre": {"pitch": 2, "high_pass": 200, "low_pass": 12000, "reverb_on": False, "room_size": 0, "chorus_on": False, "delay_on": False},
            "Clear Voice": {"pitch": 0, "high_pass": 120, "low_pass": 18000, "reverb_on": False, "room_size": 0, "chorus_on": False, "delay_on": False},
            "Spacious": {"pitch": 0, "high_pass": 100, "low_pass": 20000, "reverb_on": True, "room_size": 0.8, "chorus_on": False, "delay_on": True},
        }

        self.title("V-Change")
        self.geometry("500x700")
        self.minsize(400, 500)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        ctk.set_appearance_mode("dark")

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Top Frame for Global Controls ---
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, padx=10, pady=(10,0), sticky="ew")
        self.top_frame.grid_columnconfigure(1, weight=1)

        devices = self.voice_changer.get_devices()
        input_devices = {dev['name']: dev['index'] for dev in devices if dev['maxInputChannels'] > 0}
        output_devices = {dev['name']: dev['index'] for dev in devices if dev['maxOutputChannels'] > 0}
        
        ctk.CTkLabel(self.top_frame, text="Input:").grid(row=0, column=0, padx=(10,5), pady=5)
        self.input_menu = ctk.CTkOptionMenu(self.top_frame, values=list(input_devices.keys()), command=self.voice_changer.set_input_device)
        self.input_menu.grid(row=0, column=1, padx=(0,10), pady=5, sticky="ew")
        
        ctk.CTkLabel(self.top_frame, text="Output:").grid(row=1, column=0, padx=(10,5), pady=5)
        self.output_menu = ctk.CTkOptionMenu(self.top_frame, values=list(output_devices.keys()), command=self.on_output_device_select)
        self.output_menu.grid(row=1, column=1, padx=(0,10), pady=5, sticky="ew")
        
        self.volume_meter = ctk.CTkProgressBar(self.top_frame, progress_color="green", orientation="horizontal")
        self.volume_meter.set(0)
        self.volume_meter.grid(row=2, column=0, columnspan=2, padx=10, pady=(10,10), sticky="ew")

        # --- Tab View ---
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        self.shaping_tab = self.tab_view.add("Voice Shaping")
        self.fx_tab = self.tab_view.add("Ambience & FX")
        
        # --- Voice Shaping Tab Content ---
        self.pitch_label = ctk.CTkLabel(self.shaping_tab, text="Pitch Shift: 0.0")
        self.pitch_label.pack(padx=10, pady=(10,0))
        self.pitch_slider = ctk.CTkSlider(self.shaping_tab, from_=-12, to=12, number_of_steps=48, command=self._update_all_effects)
        self.pitch_slider.pack(padx=10, pady=(0,15), fill="x")

        self.high_pass_label = ctk.CTkLabel(self.shaping_tab, text="High-Pass (Cuts Lows): 0 Hz")
        self.high_pass_label.pack(padx=10, pady=(10,0))
        self.high_pass_slider = ctk.CTkSlider(self.shaping_tab, from_=0, to=2000, command=self._update_all_effects)
        self.high_pass_slider.pack(padx=10, pady=(0,15), fill="x")

        self.low_pass_label = ctk.CTkLabel(self.shaping_tab, text="Low-Pass (Cuts Highs): 22000 Hz")
        self.low_pass_label.pack(padx=10, pady=(10,0))
        self.low_pass_slider = ctk.CTkSlider(self.shaping_tab, from_=500, to=22000, command=self._update_all_effects)
        self.low_pass_slider.pack(padx=10, pady=(0,15), fill="x")
        
        self.reverb_switch = ctk.CTkSwitch(self.fx_tab, text="Reverb", command=self._update_all_effects)
        self.reverb_switch.pack(padx=10, pady=10, anchor="w")
        self.reverb_slider = ctk.CTkSlider(self.fx_tab, from_=0, to=1, command=self._update_all_effects)
        self.reverb_slider.pack(padx=10, pady=(0,15), fill="x")

        self.chorus_switch = ctk.CTkSwitch(self.fx_tab, text="Chorus", command=self._update_all_effects)
        self.chorus_switch.pack(padx=10, pady=10, anchor="w")

        self.delay_switch = ctk.CTkSwitch(self.fx_tab, text="Delay", command=self._update_all_effects)
        self.delay_switch.pack(padx=10, pady=10, anchor="w")

        self.presets_frame = ctk.CTkFrame(self)
        self.presets_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.presets_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.presets_frame, text="Presets").pack()
        self.preset_menu = ctk.CTkOptionMenu(self.presets_frame, values=["Normal"], command=self.apply_preset_by_name)
        self.preset_menu.pack(pady=5, padx=10, fill="x")
        self.preset_buttons_frame = ctk.CTkFrame(self.presets_frame, fg_color="transparent")
        self.preset_buttons_frame.pack(pady=5, padx=10, fill="x")
        self.preset_buttons_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(self.preset_buttons_frame, text="Save Current", command=self.save_current_preset).grid(row=0, column=0, padx=(0, 5), sticky="ew")
        ctk.CTkButton(self.preset_buttons_frame, text="Delete Preset", command=self.open_delete_preset_dialog).grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # --- Footer Frame ---
        self.footer_frame = ctk.CTkFrame(self, height=100)
        self.footer_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self.footer_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(self.footer_frame, text="Status: Off", font=("Arial", 16))
        self.status_label.grid(row=0, column=0, columnspan=2, pady=(10,5))

        self.button_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        self.button_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.button_frame.grid_columnconfigure((0,1), weight=1)
        self.start_button = ctk.CTkButton(self.button_frame, text="Start", command=self.start_voice_changer)
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.stop_button = ctk.CTkButton(self.button_frame, text="Stop", command=self.stop_voice_changer, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        self.test_switch = ctk.CTkSwitch(self.footer_frame, text="Test My Voice", command=self.toggle_test_mode)
        self.test_switch.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        self.load_presets()
        self.on_output_device_select(self.output_menu.get())

    def _update_all_effects(self, *args):
        pitch = self.pitch_slider.get()
        high_pass = self.high_pass_slider.get()
        low_pass = self.low_pass_slider.get()
        reverb_on = self.reverb_switch.get() == 1
        room_size = self.reverb_slider.get()
        chorus_on = self.chorus_switch.get() == 1
        delay_on = self.delay_switch.get() == 1

        self.pitch_label.configure(text=f"Pitch Shift: {round(pitch, 2)}")
        self.high_pass_label.configure(text=f"High-Pass (Cuts Lows): {int(high_pass)} Hz")
        self.low_pass_label.configure(text=f"Low-Pass (Cuts Highs): {int(low_pass)} Hz")
        self.reverb_slider.configure(state="normal" if reverb_on else "disabled")

        self.voice_changer.update_effects(
            pitch=pitch, high_pass=high_pass, low_pass=low_pass,
            reverb_on=reverb_on, room_size=room_size,
            chorus_on=chorus_on, delay_on=delay_on)

    def update_volume_meter(self, rms_val):
        normalized_volume = min(rms_val / 5000.0, 1.0)
        self.after(0, lambda: self.volume_meter.set(normalized_volume))

    def on_output_device_select(self, device_name):
        devices = self.voice_changer.get_devices()
        output_devices = {dev['name']: dev['index'] for dev in devices if dev['maxOutputChannels'] > 0}
        self.selected_output_device_index = output_devices.get(device_name)
        
        if self.test_switch.get() == 0:
            was_active = self.voice_changer.stream_active
            if was_active: self.voice_changer.stop()
            self.voice_changer.set_output_device(self.selected_output_device_index)
            if was_active: self.voice_changer.start()

    def toggle_test_mode(self):
        is_testing = self.test_switch.get() == 1
        was_active = self.voice_changer.stream_active
        
        if was_active:
            self.voice_changer.stop()

        if is_testing:
            default_speaker_index = self.voice_changer.p.get_default_output_device_info()['index']
            self.voice_changer.set_output_device(default_speaker_index)
            self.output_menu.configure(state="disabled")
        else:
            self.voice_changer.set_output_device(self.selected_output_device_index)
            if not self.voice_changer.stream_active:
                 self.output_menu.configure(state="normal")

        if was_active:
            self.voice_changer.start()

    def apply_preset_by_name(self, name):
        if name in self.presets:
            self.preset_menu.set(name)
            preset = self.presets[name]
            self.pitch_slider.set(preset.get("pitch", 0))
            self.high_pass_slider.set(preset.get("high_pass", 0))
            self.low_pass_slider.set(preset.get("low_pass", 22000))
            self.reverb_slider.set(preset.get("room_size", 0))
            
            if preset.get("reverb_on", False): self.reverb_switch.select()
            else: self.reverb_switch.deselect()
            
            if preset.get("chorus_on", False): self.chorus_switch.select()
            else: self.chorus_switch.deselect()

            if preset.get("delay_on", False): self.delay_switch.select()
            else: self.delay_switch.deselect()
            
            self._update_all_effects()

    def save_current_preset(self):
        dialog = ctk.CTkInputDialog(text="Enter preset name:", title="Save Preset")
        name = dialog.get_input()
        if name and name not in self.presets:
            self.presets[name] = {
                "pitch": self.pitch_slider.get(),
                "high_pass": self.high_pass_slider.get(),
                "low_pass": self.low_pass_slider.get(),
                "reverb_on": self.reverb_switch.get() == 1,
                "room_size": self.reverb_slider.get(),
                "chorus_on": self.chorus_switch.get() == 1,
                "delay_on": self.delay_switch.get() == 1,
            }
            self.save_presets_to_file()
            self.update_preset_menu()
            self.preset_menu.set(name)

    def open_delete_preset_dialog(self):
        deletable_presets = [p for p in self.presets.keys() if p not in self.default_presets]

        if not deletable_presets:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Delete Preset")
        dialog.geometry("300x150")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Select preset to delete:").pack(padx=20, pady=(10, 0))
        preset_to_delete_var = ctk.StringVar(value=deletable_presets[0])
        option_menu = ctk.CTkOptionMenu(dialog, variable=preset_to_delete_var, values=deletable_presets)
        option_menu.pack(padx=20, pady=10, fill="x")

        def confirm_delete():
            name_to_delete = preset_to_delete_var.get()
            if name_to_delete in self.presets:
                del self.presets[name_to_delete]
                self.save_presets_to_file()
                self.update_preset_menu()
            dialog.destroy()

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)
        ctk.CTkButton(button_frame, text="Delete", command=confirm_delete).pack(side="left", padx=10)
        ctk.CTkButton(button_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=10)

    def update_preset_menu(self):
        self.preset_menu.configure(values=list(self.presets.keys()))
        if self.presets and self.preset_menu.get() not in self.presets:
            self.preset_menu.set(list(self.presets.keys())[0])
            
    def load_presets(self):
        self.presets = self.default_presets.copy()
        if os.path.exists(PRESETS_FILE):
            try:
                with open(PRESETS_FILE, "r") as f:
                    user_presets = json.load(f)
                    self.presets.update(user_presets)
            except (json.JSONDecodeError, IOError):
                pass 
        self.update_preset_menu()
        self.apply_preset_by_name("Normal")

    def save_presets_to_file(self):
        user_presets = {k: v for k, v in self.presets.items() if k not in self.default_presets}
        try:
            with open(PRESETS_FILE, "w") as f:
                json.dump(user_presets, f, indent=4)
        except IOError:
            pass

    def start_voice_changer(self):
        self.voice_changer.start()
        self.status_label.configure(text="Status: Active", text_color="green")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.input_menu.configure(state="disabled")
        self.output_menu.configure(state="disabled")
        self.tab_view.configure(state="disabled")

    def stop_voice_changer(self):
        self.voice_changer.stop()
        self.status_label.configure(text="Status: Off", text_color="red")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.input_menu.configure(state="normal")
        if self.test_switch.get() == 0:
            self.output_menu.configure(state="normal")
        self.tab_view.configure(state="normal")

    def on_closing(self):
        self.save_presets_to_file()
        self.voice_changer.stop()
        self.destroy()

if __name__ == '__main__':
    app = App()
    app.mainloop() 