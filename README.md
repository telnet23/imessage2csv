# imessage2csv
Export contacts and chat messages from iOS or macOS for easy viewing and searching

Command-Line Interface
-

```
python -m imessage2csv > messages.csv
```

Python Module
-

```python
from imessage2csv import Reader

reader = Reader()

reader.add(...)
reader.add(...)
reader.add(...)
...

messages = reader.read()
```
