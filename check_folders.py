import os

BASE = 'D:/1c_ai_data'
for dataset in ['1c_forums', '1c_ebench', 'spider1c']:
    d = os.path.join(BASE, dataset)
    if os.path.exists(d):
        files = [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
        print(dataset + ':', len(files), 'files')
        for f in files[:3]:
            print(' - ' + f)
    else:
        print(dataset + ': folder not found')