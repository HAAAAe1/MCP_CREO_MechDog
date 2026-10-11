"""Final real MCP coordinate sketch regression; journal prevents uncertain retries."""
import argparse,asyncio,json,math,sys,time,uuid
from pathlib import Path
from mcp import Client
from mcp.client.stdio import StdioServerParameters
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.test_multisection_blend import stl_vertices,plane_boundary
from version import VERSION
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=ROOT/'build/sketch_stability_integration.json')
parser.add_argument('--resume',action='store_true',help='Inspect journaled tasks instead of resubmitting them; use the same installation and output')
args=parser.parse_args()
OUT=args.output.resolve()
if OUT.is_file() and not args.resume:raise SystemExit('Output already exists; use --resume or choose a new --output')
if args.resume and not OUT.is_file():raise SystemExit('No journal to resume')
r=json.loads(OUT.read_text(encoding='utf-8')) if OUT.is_file() else {'version':VERSION,'steps':{},'cases':[],'success':False}
assert r['version']==VERSION,'Journal belongs to another server version; inspect it separately'
OUT.parent.mkdir(parents=True,exist_ok=True)
r['success']=False
def save():OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
def capsule(angle,shift):
 a=math.radians(angle)
 def p(x,y):return [shift[0]+x*math.cos(a)-y*math.sin(a),shift[1]+x*math.sin(a)+y*math.cos(a)]
 return [dict(type='line',name='top',start=p(-10000,5000),end=p(10000,5000)),dict(type='arc',name='right',center=p(10000,0),radius=5000,start_angle=-90+angle,end_angle=90+angle),
 dict(type='line',name='bottom',start=p(10000,-5000),end=p(-10000,-5000)),dict(type='arc',name='left',center=p(-10000,0),radius=5000,start_angle=90+angle,end_angle=270+angle)]
def lines(points):return [dict(type='line',name=f'edge_{i}',start=p,end=points[(i+1)%len(points)]) for i,p in enumerate(points)]
def area(entities):return abs(sum(e['start'][0]*e['end'][1]-e['end'][0]*e['start'][1] for e in entities))/2
original=json.loads((ROOT/'examples/sketch_stability_large_profile.json').read_text())
regular=lines([[40000*math.cos(2*math.pi*i/12),40000*math.sin(2*math.pi*i/12)] for i in range(12)])
rectangle=[dict(type='rectangle',name='box',min=[-50,-40],max=[50,40])]
specs=[('report19','XY',0,original,area(original),'polygon',0,[0,0],'auto'),
 ('polygon12','XY',0,regular,area(regular),'polygon',0,[0,0],'auto'),
 ('capsule_xy','XY',0,capsule(0,[0,0]),20000*10000+math.pi*5000**2,'capsule',0,[0,0],'auto'),
 ('capsule_xz','XZ',25,capsule(30,[30000,20000]),20000*10000+math.pi*5000**2,'capsule',30,[30000,20000],'auto'),
 ('circle_yz','YZ',10,[dict(type='circle',name='circle',center=[30000,20000],radius=5000)],math.pi*5000**2,'circle',0,[30000,20000],'auto'),
 ('rectangle_coordinates','XY',0,rectangle,8000,'rectangle',0,[0,0],'coordinates')]
def summary(p):
 result=p['result'];assert result['saved_file_reloaded_and_verified']
 aliases=result['aliases'];assert result['inspection']['healthy'] and result['inspection']['has_solid']
 assert aliases['profile']['solver']['used']=='coordinates'
 return dict(model_id=p['model_id'],revision=p['revision'],sketch_feature_id=aliases['profile']['feature_id'],
  solid_feature_id=aliases['solid']['feature_id'],volume_mm3=result['inspection']['volume_mm3'],solver=aliases['profile']['solver'],saved_file_reloaded_and_verified=True)
def boundary(p,kind,entities,angle,shift,x_factor,y_factor):
 result=p['result'];frame=result['aliases']['profile'];origin,u,v,n=[frame[k] for k in ('origin','u_axis','v_axis','normal')]
 local=[]
 for triangle in stl_vertices(next(x['file'] for x in result['operations'] if x['op']=='export')):
  converted=[]
  for vertex in triangle:
   delta=[vertex[i]-origin[i] for i in range(3)]
   converted.append([sum(delta[i]*axis[i] for i in range(3)) for axis in (u,v,n)])
  local.append(converted)
 points=plane_boundary(local,100);assert points
 if kind=='polygon':expected=[[e['start'][0]*x_factor,e['start'][1]*y_factor] for e in entities]
 elif kind=='rectangle':expected=[[-50*x_factor,-40*y_factor],[50*x_factor,-40*y_factor],[50*x_factor,40*y_factor],[-50*x_factor,40*y_factor]]
 maximum=0;a=math.radians(angle)
 for p in points:
  if kind in ('polygon','rectangle'):
   distance=math.inf
   for i,q in enumerate(expected):
    b=expected[(i+1)%len(expected)];dx=b[0]-q[0];dy=b[1]-q[1];length=dx*dx+dy*dy;t=max(0,min(1,((p[0]-q[0])*dx+(p[1]-q[1])*dy)/length))
    distance=min(distance,math.hypot(p[0]-q[0]-t*dx,p[1]-q[1]-t*dy))
  else:
   assert x_factor==y_factor;dx=p[0]-shift[0]*x_factor;dy=p[1]-shift[1]*x_factor;x=dx*math.cos(a)+dy*math.sin(a);y=-dx*math.sin(a)+dy*math.cos(a)
   if kind=='circle':distance=abs(math.hypot(x,y)-5000*x_factor)
   elif abs(x)<=10000*x_factor:distance=abs(abs(y)-5000*x_factor)
   else:distance=abs(math.hypot(abs(x)-10000*x_factor,y)-5000*x_factor)
  maximum=max(maximum,distance)
 assert maximum<.15,maximum
 return {'max_deviation_mm':maximum,'tolerance_mm':.15,'boundary_point_count':len(points)}
def scaled_geometry(entities,x,y):
 result=json.loads(json.dumps(entities))
 for e in result:
  for key in ('start','end','center','min','max'):
   if key in e:e[key]=[e[key][0]*x,e[key][1]*y]
  if 'radius' in e:assert x==y;e['radius']*=x
 return result
async def main():
 async with Client(StdioServerParameters(command=sys.executable,args=[str(ROOT/'server.py')],cwd=ROOT)) as client:
  async def job(stage,tool,args,failure=False):
   if stage not in r['steps']:
    response=await client.call_tool(tool,args);assert not response.is_error,str(response)
    r['steps'][stage]={'job_id':response.structured_content['job_id'],'tool':tool};save();print(stage+' '+r['steps'][stage]['job_id'],flush=True)
   deadline=time.monotonic()+600
   while True:
    response=await client.call_tool('creo_get_job',{'job_id':r['steps'][stage]['job_id']});assert not response.is_error
    p=response.structured_content
    if p['status'] in ('succeeded','failed','unknown_outcome'):break
    if time.monotonic()>deadline:raise RuntimeError('Inspect pending job, never resubmit')
    await asyncio.sleep(.7)
   assert p['status']==('failed' if failure else 'succeeded'),p.get('message')
   if failure:assert p['result']['rollback_succeeded']
   return p
  for name,plane,offset,entities,square,kind,angle,shift,mode in specs:
   row=next((x for x in r['cases'] if x['name']==name),None)
   if row is None:row={'name':name,'passed':False};r['cases'].append(row)
   initial=await job(name+'_create','creo_execute_plan',{'model_name':'stb_'+uuid.uuid4().hex[:8],
    'operations':[dict(op='sketch',label='profile',plane=plane,offset=offset,entities=entities,dimensioning=mode),dict(op='extrude',label='solid',sketch='profile',depth=100),dict(op='export',format='stl')],
    'assertions':{'require_solid':True,'volume_mm3':square*100,'volume_tolerance':max(1,square*100*1e-8)}})
   row['initial']=summary(initial);row['initial']['boundary']=boundary(initial,kind,entities,angle,shift,1,1);save()
   ids=initial['result']['aliases']['profile']['dimension_ids'];f=next(x for x in initial['result']['inspection']['features'] if x['id']==row['initial']['sketch_feature_id'])
   values={d['id']:d['value'] for d in f['sketch_dimensions']};factor=1.02 if kind in ('polygon','rectangle') else 1.01
   edits={key:values[dim]*factor for key,dim in ids.items() if (key.endswith('_x') if kind in ('polygon','rectangle') else not key.endswith('_angle'))}
   assert edits
   edited=await job(name+'_edit','creo_execute_plan',{'model_id':initial['model_id'],'expected_revision':initial['revision'],
    'operations':[dict(op='set_sketch_dimensions',sketch='profile',values=edits),dict(op='export',format='stl')],
    'assertions':{'require_solid':True,'volume_mm3':square*100*(factor if kind in ('polygon','rectangle') else factor**2),'volume_tolerance':max(1,square*100*1e-8)}})
   row['edited']=summary(edited);row['edited']['boundary']=boundary(edited,kind,entities,angle,shift,factor,1 if kind in ('polygon','rectangle') else factor)
   for k in ('sketch_feature_id','solid_feature_id'):assert row['initial'][k]==row['edited'][k]
   save()
   if name in ('report19','capsule_xy'):
    x,y=(1.03,1.02) if name=='report19' else (1.02,1.02)
    geometry=await job(name+'_geometry','creo_update_sketch_geometry',{'model_id':edited['model_id'],'expected_revision':edited['revision'],'sketch':'profile','entities':scaled_geometry(entities,x,y)})
    row['geometry_edit']=summary(geometry)
    exported=await job(name+'_geometry_export','creo_export_model',{'model_id':geometry['model_id'],'format':'stl'})
    row['geometry_edit']['boundary']=boundary(exported,kind,entities,angle,shift,x,y)
    assert abs(row['geometry_edit']['volume_mm3']-square*100*x*y)<max(1,square*100*1e-8)
    for k in ('sketch_feature_id','solid_feature_id'):assert row['geometry_edit'][k]==row['initial'][k]
    save()
    key=next(k for k in geometry['result']['aliases']['profile']['dimension_ids'] if k.endswith('_x'))
    failed=await job(name+'_rollback','creo_execute_plan',{'model_id':geometry['model_id'],'expected_revision':geometry['revision'],
     'operations':[dict(op='set_sketch_dimensions',sketch='profile',values={key:20000})],'assertions':{'volume_mm3':0}},True)
    refreshed=await job(name+'_refresh','creo_refresh_model',{'model_id':geometry['model_id']})
    assert refreshed['revision']==geometry['revision']
    assert abs(refreshed['result']['inspection']['volume_mm3']-row['geometry_edit']['volume_mm3'])<.01
    row['rollback_succeeded']=True;row['rollback_live_verified']=True
   row['passed']=True;save();print('CASE_PASS '+name,flush=True)
  r['success']=len(r['cases'])==6 and all(x['passed'] for x in r['cases']);save();print('PUBLIC_COORDINATES_PASS',flush=True)
asyncio.run(main())
