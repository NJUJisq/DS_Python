# Towards Better Dependency Management: A First Look at Dependency Smells in Python Projects
This repository stores the source code of PyCD and all materials in this study

We studied three dependency smells in Python projects.
- Missing dependency
- Bloated dependency
- Version constraint inconsistency

## Materials
The following sections describe the main materials included in this repository.    
[PyCD](https://github.com/NJUJisq/DS_Python/tree/master/PyCD). This folder stores the source code of PyCD. 

[Extracting Imports](https://github.com/NJUJisq/DS_Python/tree/master/Extracting%20Imports). This folder stores the source code that extracts dependency relations from source code 

[Evaluation of PyCD](https://github.com/NJUJisq/DS_Python/tree/master/Evaluation%20of%20PyCD/result). This folder stores all results of the approaches (PyCD, GDG, and Libraries.io). In particular, "Evaluation of PyCD/Truth" stores our constructed ground truth.

The evaluation dataset is constructed from open-source projects in Github. You can find the name of these project in "Evaluation of PyCD/evaluate_pycd_212.xlsx". 

[Empirical Study](https://github.com/NJUJisq/DS_Python/tree/master/Empirical%20Study). This folder stores the results for emipircal study.
Our empirical study is conducted on 132 open-source Python projects in Github. You can find the name of these projects in "Empirical Study/Details of 132 projects.xlsx" folder. 

[Harmful DS report](https://github.com/NJUJisq/DS_Python/tree/master/Harmful%20DS%20report) This folder stores the list of the links to 39 reported issues for harmful dependency smells.
