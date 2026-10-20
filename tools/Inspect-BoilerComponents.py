from PIL import Image
import numpy as np,sys
a=np.asarray(Image.open(sys.argv[1]).convert('RGB').resize((540,960)))
r,g,b=[a[:,:,i].astype(int) for i in range(3)];m=(r>145)&(g<130)&(r>g*1.5)&(r>b*1.2);seen=np.zeros(m.shape,dtype=bool);out=[]
for y,x in zip(*np.nonzero(m)):
 if seen[y,x]:continue
 stack=[(y,x)];seen[y,x]=True;pts=[]
 while stack:
  yy,xx=stack.pop();pts.append((yy,xx))
  for ny,nx in ((yy-1,xx),(yy+1,xx),(yy,xx-1),(yy,xx+1)):
   if 0<=ny<960 and 0<=nx<540 and m[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;stack.append((ny,nx))
 if len(pts)<10:continue
 ys,xs=zip(*pts);x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys);w=x1-x0+1;h=y1-y0+1
 out.append((len(pts),x0*2,y0*2,w*2,h*2))
print(sorted(out,reverse=True)[:20])
