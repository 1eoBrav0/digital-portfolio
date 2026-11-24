"""Reproducible 30s vertical motion study using FFmpeg and generated artwork."""
import argparse
import math
import struct
import subprocess
import wave
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--ffmpeg',default='ffmpeg')
args=p.parse_args()
root=Path(__file__).resolve().parent
work=root/'render-work'
work.mkdir(exist_ok=True)

# Original soft pulse, 96 BPM. No samples or third-party music.
with wave.open(str(work/'pulse.wav'),'wb') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(48000)
    for sec in range(30):
        block=bytearray()
        for n in range(48000):
            t=sec+n/48000
            beat=t%0.625
            kick=0.23*math.exp(-beat*24)*math.sin(2*math.pi*(58*beat+3*(1-math.exp(-beat*30))))
            note=[220,261.6256,329.6276,293.6648][int(t/2.5)%4]
            chord=0.055*math.sin(2*math.pi*note*t)*math.exp(-(t%0.625)*5)
            envelope=min(1,t/1.5,(30-t)/2)
            block.extend(struct.pack('<h',int(32767*envelope*(kick+chord))))
        wav.writeframes(block)
for i in range(1,7):
    # Slow camera drift plus dissolves through black keep all lettering legible.
    vf="zoompan=z='1+0.035*on/149':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=150:s=1080x1920:fps=30,fade=t=in:d=0.32,fade=t=out:st=4.65:d=0.35,format=yuv420p"
    subprocess.run([args.ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(root/'frames'/f'scene-{i}.png'),'-vf',vf,'-frames:v','150','-c:v','libx264','-preset','fast','-crf','20','-threads','4',str(work/f'{i}.mp4')],check=True)
    print(f'Scene {i}/6 rendered',flush=True)
(work/'concat.txt').write_text(''.join(f"file '{i}.mp4'\n" for i in range(1,7)),encoding='utf-8')
subprocess.run([args.ffmpeg,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i','concat.txt','-i','pulse.wav','-c:v','copy','-c:a','aac','-b:a','160k','-t','30','-movflags','+faststart',str(root/'ser-motion.mp4')],cwd=work,check=True)
print('Exported ser-motion.mp4: 1080x1920, 30 fps, 30 seconds.',flush=True)
