import pstats
p = pstats.Stats('Narmer.prof')
p.sort_stats('time').print_stats(20)