from ovito.io import import_file
p = import_file('/home/fyq/lammps_ZrCu/dumps/Glass_Cu50Zr50_N5000_300K_equilibrated.dump')
d = p.compute()
types = d.particles.particle_types
print(types, type(types))
print('types attrs', [x for x in dir(types) if 'mutable' in x.lower() or 'type' in x.lower()][:40])
print('ptype obj', types.types[0], type(types.types[0]))
print('ptype attrs', [x for x in dir(types.types[0]) if 'mutable' in x.lower() or x in ('name','radius','id')][:80])
print('has make_mutable', hasattr(types, 'make_mutable'))