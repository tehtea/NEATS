import shelve

with shelve.open('userdata') as db:
    for i in (db.items()):
        print(i)
