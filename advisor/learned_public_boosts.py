"""Causal protocol projection for versioned V5 references only.

Legacy summaries are unchanged. Missing public evidence propagates as None.
No checkpoint, opposing request or future state is read.
"""
STATS=('atk','def','spa','spd','spe','accuracy','evasion')
VERSION='showdown-public-boost-projection-v1'

def public_boosts(history):
    rows={};active={};last_move={}
    def blank(known):return {s:0 if known else None for s in STATS}
    for line in history:
        p=line.split('|')
        if len(p)<2:continue
        kind=p[1];a=p[2:]
        if kind=='-clearallboost':
            for ident in active.values():rows[ident]=blank(True)
            continue
        if not a or not a[0].startswith(('p1a: ','p2a: ')):continue
        ident=a[0];role=ident[:2]
        if kind in ('switch','drag'):
            rows[ident]=blank(last_move.get(role)!='Baton Pass');active[role]=ident;last_move.pop(role,None)
        if kind=='replace':
            rows[ident]=dict(rows.get(active.get(role),blank(False)));active[role]=ident
        row=rows.setdefault(ident,blank(False))
        if kind=='move' and len(a)>1:last_move[role]=a[1]
        elif kind=='faint':rows[ident]=blank(True)
        elif kind in ('-boost','-unboost','-setboost') and len(a)>2 and a[1] in STATS:
            stat=a[1];amount=int(a[2]);old=row[stat]
            value=amount if kind=='-setboost' else None if old is None else old+(amount if kind=='-boost' else -amount)
            row[stat]=None if value is None else max(-6,min(6,value))
        elif kind=='-clearboost':rows[ident]=blank(True)
        elif kind in ('-clearpositiveboost','-clearnegativeboost','-invertboost'):
            for stat,value in row.items():
                if value is not None:row[stat]=-value if kind=='-invertboost' else min(0,value) if kind=='-clearpositiveboost' else max(0,value)
        elif kind in ('-copyboost','-swapboost') and len(a)>1:
            other=rows.setdefault(a[1],blank(False))
            selected=tuple(s.strip() for s in a[2].split(',')) if len(a)>2 and not a[2].startswith('[') else STATS
            for stat in selected:
                if stat not in STATS:continue
                if kind=='-swapboost':row[stat],other[stat]=other[stat],row[stat]
                else:row[stat]=other[stat]
    return rows
