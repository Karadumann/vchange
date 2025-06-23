import pyaudio
import numpy as np
import pyrubberband as pyrb
import threading
import customtkinter as ctk

class VoiceChanger:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream_active = False
        self.thread = None

        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.pitch_shift = 0.0

        self.input_device_index = self.p.get_default_input_device_info()['index']
        self.output_device_index = self.p.get_default_output_device_info()['index']

    def set_pitch(self, pitch):
        self.pitch_shift = pitch
        
    def set_input_device(self, index):
        self.input_device_index = index

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
        except OSError as e:
            print(f"Cihaz açılırken hata oluştu: {e}")
            self.stream_active = False
            return

        while self.stream_active:
            try:
                data = stream_in.read(self.CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                if self.pitch_shift != 0:
                    pitched_audio = pyrb.pitch_shift(audio_data, self.RATE, self.pitch_shift)
                    processed_data = pitched_audio.astype(np.int16).tobytes()
                else:
                    processed_data = data

                stream_out.write(processed_data)
            except IOError:
                self.stream_active = False

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

        self.title("V-Change")
        self.geometry("500x400")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        ctk.set_appearance_mode("dark")

        devices = self.voice_changer.get_devices()
        input_devices = {dev['name']: dev['index'] for dev in devices if dev['maxInputChannels'] > 0}
        output_devices = {dev['name']: dev['index'] for dev in devices if dev['maxOutputChannels'] > 0}

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(self.main_frame, text="Giriş Cihazı (Mikrofon):").pack(anchor="w", padx=10)
        self.input_menu = ctk.CTkOptionMenu(self.main_frame, values=list(input_devices.keys()), command=lambda name: self.voice_changer.set_input_device(input_devices[name]))
        self.input_menu.pack(padx=10, pady=(0, 10), fill="x")
        
        ctk.CTkLabel(self.main_frame, text="Çıkış Cihazı (Hoparlör/Sanal Kablo):").pack(anchor="w", padx=10)
        self.output_menu = ctk.CTkOptionMenu(self.main_frame, values=list(output_devices.keys()), command=lambda name: self.voice_changer.set_output_device(output_devices[name]))
        self.output_menu.pack(padx=10, pady=(0, 20), fill="x")

        self.pitch_label = ctk.CTkLabel(self.main_frame, text="Pitch: 0.0")
        self.pitch_label.pack()
        
        self.pitch_slider = ctk.CTkSlider(self.main_frame, from_=-12, to=12, number_of_steps=48, command=self.update_pitch)
        self.pitch_slider.set(0)
        self.pitch_slider.pack(padx=10, pady=5, fill="x")

        self.status_label = ctk.CTkLabel(self.main_frame, text="Durum: Kapalı", font=("Arial", 16))
        self.status_label.pack(pady=10)
        
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(pady=10)

        self.start_button = ctk.CTkButton(self.button_frame, text="Başlat", command=self.start_voice_changer)
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ctk.CTkButton(self.button_frame, text="Durdur", command=self.stop_voice_changer, state="disabled")
        self.stop_button.pack(side="left", padx=5)

    def update_pitch(self, value):
        pitch_value = round(value, 2)
        self.pitch_label.configure(text=f"Pitch: {pitch_value}")
        self.voice_changer.set_pitch(pitch_value)

    def start_voice_changer(self):
        self.voice_changer.start()
        self.status_label.configure(text="Durum: Aktif", text_color="green")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.input_menu.configure(state="disabled")
        self.output_menu.configure(state="disabled")

    def stop_voice_changer(self):
        self.voice_changer.stop()
        self.status_label.configure(text="Durum: Kapalı", text_color="red")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.input_menu.configure(state="normal")
        self.output_menu.configure(state="normal")

    def on_closing(self):
        self.voice_changer.stop()
        self.destroy()

if __name__ == '__main__':
    app = App()
    app.mainloop() 