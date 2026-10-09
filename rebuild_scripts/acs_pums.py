import zipfile, pandas as pd, numpy as np
FIPS = {"CA":6,"TX":48,"NY":36,"FL":12,"MA":25,"NC":37,"IL":17,"WA":53}
frames = []
for st in FIPS:
    z = zipfile.ZipFile(f'csv_p{st.lower()}.zip')
    name = [n for n in z.namelist() if n.endswith('.csv')][0]
    d = pd.read_csv(z.open(name), usecols=['STATE','AGEP','PWGTP','MIG','MIGSP'])
    d = d.rename(columns={'STATE':'ST'}); d = d[(d.AGEP >= 18) & (d.AGEP <= 35)].copy(); d['state'] = st; d['file'] = name
    frames.append(d)
d = pd.concat(frames); d.to_pickle('young.pkl')
for label, valid in [('1-56', d.MIGSP.between(1,56)), ('1-56+72', d.MIGSP.between(1,56) | (d.MIGSP==72))]:
    mv = (d.MIG == 3) & valid & (d.MIGSP != d.ST)
    print(label, d.PWGTP.sum(), d.PWGTP[mv].sum(), len(d), mv.sum(), d.PWGTP[mv].sum()/d.PWGTP.sum())
