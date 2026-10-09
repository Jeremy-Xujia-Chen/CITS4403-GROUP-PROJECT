"""Render the executed notebook's accepted migration events to an offline MP4."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
import imageio_ffmpeg
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter
from matplotlib.patches import Circle,PathPatch,Rectangle
from matplotlib.path import Path as PlotPath
import numpy as np

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events',type=Path,default=ROOT / 'results/calibrated/migration-events.json')
    parser.add_argument('--output',type=Path,default=ROOT / 'results/calibrated/migration-comparison.mp4')
    parser.add_argument('--fps',type=int,default=24)
    parser.add_argument('--seconds-per-year',type=float,default=2.5)
    args = parser.parse_args()
    data = json.loads(args.events.read_text(encoding='utf-8'))
    scenarios = data['scenarios']
    assert len(scenarios)==2
    years = len(scenarios[0]['frames'])
    assert all(len(s['frames'])==years for s in scenarios)
    assert args.fps>0 and args.seconds_per_year>0
    per_year = round(args.fps*args.seconds_per_year)
    assert per_year>=2
    positions = {s:np.array([70+(lon+124)/57*780,410-(lat-25)/25*350])
                 for s,(lat,lon) in data['states'].items()}
    target = data['target']
    bg,panel,muted,ink = '#08141e','#10232f','#9cb3be','#e7f1f4'
    mint,blue,gold = '#75e2b6','#a6ddff','#ffc977'
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':ink,'font.size':11})
    fig = plt.figure(figsize=(12.8,7.2),dpi=100,facecolor=bg)
    fig.text(.04,.94,'MIGRATION LAB / RECORDED MODEL EVENTS',color=mint,fontsize=10,weight='bold')
    heading = fig.text(.04,.88,'Interstate migration',fontsize=25,weight='bold')
    fig.text(.04,.83,f"Same seed {data['seed']}  |  {scenarios[0]['n_agents']} agents per scenario  |  {target} policy target",color=muted)
    panels = []
    for i,scenario in enumerate(scenarios):
        left = .04+i*.48
        ax = fig.add_axes([left,.29,.44,.43],facecolor=panel)
        ax.set_xlim(0,920); ax.set_ylim(470,0); ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color('#253e4c')
        for x in range(110,910,130): ax.axvline(x,color='#24404e',ls=(0,(2,6)),lw=.6)
        for y in range(60,450,90): ax.axhline(y,color='#24404e',ls=(0,(2,6)),lw=.6)
        fig.text(left,.755,scenario['name'].replace(' · intensity 1',' (intensity 1)'),fontsize=15,weight='bold')
        stats = fig.text(left,.245,'',fontsize=11)
        nodes = {}
        for state,p in positions.items():
            circle = Circle(p,13,facecolor='#163342',edgecolor=mint if state==target else '#7ea2b5',lw=2 if state==target else 1,zorder=3)
            ax.add_patch(circle)
            dx,dy = (20,-24) if state=='MA' else (-17,33) if state=='NY' else (0,32)
            ax.text(p[0]+dx,p[1]+dy,state,ha='center',fontsize=10,weight='bold',color=ink,zorder=5)
            label = ax.text(p[0]+dx,p[1]+dy+20,'',ha='center',fontsize=8,color=muted,zorder=5)
            nodes[state]=(circle,label)
        dots = ax.scatter([],[],zorder=4,edgecolors='none')
        panels.append({'ax':ax,'nodes':nodes,'dots':dots,'stats':stats,'routes':[]})
    fig.text(.04,.19,'BLUE = accepted agent move    GOLD = social-chain move    GREEN RING = policy target',fontsize=10,color=muted)
    bar = Rectangle((.04,.145),0,.007,transform=fig.transFigure,facecolor=mint,edgecolor='none')
    fig.add_artist(Rectangle((.04,.145),.92,.007,transform=fig.transFigure,facecolor='#253e4c',edgecolor='none'))
    fig.add_artist(bar)
    fig.text(.04,.10,'One point = one accepted move. Annual timing and curved paths are illustrative.',fontsize=10,color=muted)
    fig.text(.04,.065,'Labels show end-year residents, including demographic replacement. Closed eight-state simulation.',fontsize=10,color=muted)
    active_year = -1
    def rebuild(year_index):
        nonlocal active_year
        active_year = year_index
        heading.set_text(f"Interstate migration | {scenarios[0]['frames'][year_index]['year']}")
        for scenario,p in zip(scenarios,panels):
            frame = scenario['frames'][year_index]
            for route in p['routes']: route.remove()
            p['routes'] = []
            for (origin,destination),count in Counter((e[0],e[1]) for e in frame['moves']).items():
                a,b = positions[origin],positions[destination]
                d=b-a; c=(a+b)/2+np.array([-d[1],d[0]])/np.linalg.norm(d)*35
                route=PathPatch(PlotPath([a,c,b],[PlotPath.MOVETO,PlotPath.CURVE3,PlotPath.CURVE3]),
                    fill=False,color=mint if destination==target else blue,alpha=.23,lw=.5+np.sqrt(count)*.5,zorder=1)
                p['ax'].add_patch(route);p['routes'].append(route)
            paths=[]
            for origin,destination,chain in frame['moves']:
                a,b=positions[origin],positions[destination];d=b-a
                c=(a+b)/2+np.array([-d[1],d[0]])/np.linalg.norm(d)*35
                paths.append([a,c,b])
            p['paths']=np.array(paths,dtype=float).reshape(-1,3,2)
            p['phases']=(np.arange(len(paths))*.61803398875)%1
            p['dots'].remove()
            p['dots']=p['ax'].scatter([],[],zorder=4,edgecolors='none')
            p['dots'].set_color([gold if e[2] else blue for e in frame['moves']])
            p['dots'].set_sizes([18 if e[2] else 10 for e in frame['moves']])
            for state,pop in frame['population'].items():
                p['nodes'][state][0].set_radius(10+np.sqrt(pop)*.5)
                p['nodes'][state][1].set_text(f'{pop} residents')
            chains=sum(e[2] for e in frame['moves']);inflow=sum(e[1]==target for e in frame['moves'])
            p['stats'].set_text(f"Accepted: {len(paths)}   |   Chains: {chains}   |   {target} inflow: {inflow}")
    def render(frame_number):
        year_index=min(years-1,frame_number//per_year)
        t=(frame_number%per_year)/(per_year-1)
        if year_index!=active_year: rebuild(year_index)
        for p in panels:
            progress=np.clip((t-p['phases']*.30)/.70,0,1)
            u=1-progress
            paths=p['paths']
            xy=u[:,None]**2*paths[:,0]+2*u[:,None]*progress[:,None]*paths[:,1]+progress[:,None]**2*paths[:,2]
            p['dots'].set_offsets(xy)
            p['dots'].set_alpha(np.where((progress>0)&(progress<1),1,.18))
        bar.set_width(.92*(year_index+t)/years)
    matplotlib.rcParams['animation.ffmpeg_path']=imageio_ffmpeg.get_ffmpeg_exe()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    writer=FFMpegWriter(fps=args.fps,codec='libx264',bitrate=2800,
                       metadata={'title':'Accepted migration events: baseline vs combined policy',
                                 'comment':'Simulated events; annual interpolation is illustrative.'},
                       extra_args=['-pix_fmt','yuv420p','-movflags','+faststart'])
    started=time.monotonic()
    frames=years*per_year
    with writer.saving(fig,str(args.output),dpi=100):
        for number in range(frames):
            render(number)
            writer.grab_frame(facecolor=bg)
            if number in [0,frames//2,frames-1,per_year//2]:
                fig.savefig(args.output.with_name(f'video-frame-{number:04d}.png'),dpi=100,facecolor=bg)
            if number%per_year==0: print(f'Encoded year {number//per_year+1}/{years}',flush=True)
    # Decode every frame, check format and verify that particles actually move.
    reader=imageio_ffmpeg.read_frames(str(args.output),pix_fmt='rgb24')
    metadata=next(reader)
    hashes={};decoded=0
    for number,pixels in enumerate(reader):
        if number in [0,per_year//2,per_year//2+1,frames//2,frames-1]:
            hashes[number]=hashlib.sha256(pixels).hexdigest()
            assert np.frombuffer(pixels,dtype=np.uint8).std()>10
        decoded+=1
    assert decoded==frames,(decoded,frames)
    assert tuple(metadata['size'])==(1280,720),metadata
    assert abs(metadata['duration']-frames/args.fps)<.15,metadata
    assert hashes[per_year//2]!=hashes[per_year//2+1]
    report={'passed':True,'output':str(args.output),'frames':decoded,'fps':metadata['fps'],
            'duration_seconds':metadata['duration'],'size':metadata['size'],'codec':metadata['codec'],
            'bytes':args.output.stat().st_size,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
            'seconds_to_render_and_verify':time.monotonic()-started,
            'seed':data['seed'],'accepted_moves':{s['name']:sum(len(f['moves']) for f in s['frames']) for s in scenarios},
            'all_frames_decoded':True,'adjacent_frames_differ':True,'audio':False}
    args.output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__': main()
