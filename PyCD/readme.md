# PyCD: Extracting dependency relations from dependency configuration  files
To use PyCD, you can run the command:
```
python3 GetDep_ast.py <pro_path> <tofile>
```
- *pro_path* refers to the path for a Python project or a configuration file.
- *tofile* refers to a **.csv** file that store the dependencies PyCD has extracted, such as 'result.csv'

PyCD supports the parsing for three common configuration files used in Python projects.
- setup.py
- requirements.txt.
- Pipfile

<!-- And it is easy to add other configuration files. -->