H=8760*3
def tco(capex, resid, kw, colo, fin, ops):
    dep = capex*(1-resid)/H
    power = kw*colo/730
    finance = capex*fin*0.6/8760
    return (dep+power+finance+ops)/8, dep/8, power/8, finance/8, ops/8
print("## Owner TCO $/GPU-h (available hour)")
cases = {
 "HGX H200": [(320e3,.25,8.5,150,0,0),(370e3,.25,10,200,.09,0.8),(420e3,0,10.5,250,.09,1.0)],
 "HGX B200": [(400e3,.25,12,150,0,0),(450e3,.25,14.3,200,.09,1.0),(500e3,0,14.3,250,.09,1.2)],
 "HGX B300": [(450e3,.25,14,150,0,0),(520e3,.25,15,200,.09,1.1),(600e3,0,15,250,.09,1.3)],
 "8x RTX PRO 6000 BSE": [(110e3,.25,6,150,0,0),(150e3,.25,7,200,.09,0.5),(190e3,0,7,250,.09,0.6)],
}
for k,v in cases.items():
    out=[tco(*c) for c in v]
    print(k, " | ".join(f"{o[0]:.2f} (dep {o[1]:.2f} pwr {o[2]:.2f} fin {o[3]:.2f} ops {o[4]:.2f})" for o in out))
print()
tao=232.45
print("## Emission")
rows=[(32,"118",0.0083,20.8),(34,"90",0.0317,15.5),(35,"105",0.0059,7.7),(50,"26",0.0035,1.2),(60,"1",0.0071,0.5),("median","-",0.00445,None)]
for r,n,p,t in rows:
    mtm=7200*0.41*p*tao
    tb = 0.41*t*tao if t is not None else None
    s=f"rank {r} SN{n}: MTM miner $/day {mtm:,.0f}"
    if tb is not None: s+=f" | TAO-backed {0.41*t:.2f} TAO = ${tb:,.0f}/day"
    for price,label in ((3.20,"H200 rented"),(2.05,"H200 owned"),(1.80,"PRO6000 rented")):
        s+=f" | {label}: MTM {mtm/price:,.0f} GPU-h ({mtm/price/24:.0f} GPUs)" + (f", TB {tb/price:,.0f} GPU-h ({tb/price/24:.1f} GPUs)" if tb is not None else "")
    print(s)
print("total TAO emission/day $", 3600*tao)
print()
print("## Stripe fee share by top-up")
for amt in (5,10,20,50,100):
    f=0.029*amt+0.30
    print(amt, f"{f:.3f}", f"{f/amt*100:.1f}%", "intl+FX", f"{(f+0.025*amt)/amt*100:.1f}%")
print("## NOWPayments: 0.5-1.5% + network fee; with $1 network fee:")
for amt in (20,50,100):
    for sf in (0.005,0.01,0.015):
        print(amt, sf, f"{(sf*amt+1)/amt*100:.1f}%")
print()
print("## R2 storage per clip (MB): per-year $, 10-year $, perpetuity@5%")
for label,mb in (("LTX 720p 5s",6),("LTX 1080p 10s",24),("LTX 2160p 10s",100),("H3 768p 5s",5),("H3 768p 14s",14)):
    yr=mb/1024*0.015*12*1.03
    print(label, mb, f"{yr:.5f}", f"{yr*10:.4f}", f"{yr/0.05:.4f}", "classA 4 writes", 4*4.5e-6)
