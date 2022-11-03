# This is a prototype of LCM package provisioning in GoodData

## Set up Python
```bash
make dev
```

## Start up GoodData
```bash
docker run -d -i -t -p 3000:3000 -p 5432:5432 -v gd-volume:/data gooddata/gooddata-cn-ce:dev_latest
```


## Provisioning try out
* [Simple definition](definitions/simple)
```bash
python3 -i core.py
```

```python
h = Hierarchy.from_definition("simple")
h.put_all()
```
* [Advanced definition](definitions/advanced)
```bash
python3 -i core.py
```

```python
h = Hierarchy.from_definition("advanced")
h.put_all()
```

* [Advanced simplified definition](definitions/advanced_simplified)
```bash
python3 -i core.py
```

```python
h1 = Hierarchy.from_definition("advanced")
h2 = Hierarchy.from_definition("advanced_simplified")
assert h1 == h2
```

* [Advanced simplified tenants definition](definitions/advanced_simplified_tenants)
```bash
python3 -i core.py
```

```python
h = Hierarchy.from_definition("advanced_simplified_tenants")
h.put_all()
```
