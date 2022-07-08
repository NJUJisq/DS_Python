# coding: utf-8
from collections import defaultdict
import ast
import os
import sys
import json
class Import_API(object):
    def __init__(self,module=None,API_name=None,lineno=0,filepath=''):
        self.module = module
        self.API_name = API_name
        self.lineno = lineno
        self.filepath = filepath
        
    def __str__(self):
        return '\n'.join([str(self.module),str(self.API_name),str(self.lineno),str(self.filepath)])
    

class APIvisitor(ast.NodeVisitor):
    def __init__(self,path):
        self.project_name = os.path.basename(path) 
        self.Third_parties = defaultdict(list)
        self.Import_APIs = defaultdict(list)
        self.path = path
        self.name_imports = []
        self.candidates = []
        self.scopes = []
        self.abs_imports = set() 
        self.stardard_libs = self.Readstardard_libs()
        self.processOne()
        self.processTwo()
    
    def Readstardard_libs(self):

        with open("stdlib.txt", "r") as f:
            data = {x.strip() for x in f}

        return data



    def processOne(self): 
        '''
        visit all import statements
        '''       
        walk = os.walk(self.path, followlinks=True)
        ignore_dirs = [".hg", ".svn", ".git", ".tox", "__pycache__", "env", "venv"]
        self.distribute_names = set()    
    
        for root, dirs, files in walk:
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
           
            self.candidates.append(os.path.abspath(root))
            self.name_imports.append(os.path.basename(root))
            self.prefix = os.path.abspath(root)+'\\'
            files = [fn for fn in files if os.path.splitext(fn)[1] == ".py" ]

            self.name_imports += [os.path.splitext(fn)[0] for fn in files]
            self.candidates += [self.prefix +os.path.splitext(fn)[0] for fn in files]
            
            for file in files:
                file_name = os.path.join(root, file)
                self.filepath = file_name                    
                try:
                    content = ''
                    if sys.version_info[0] > 2:
                        with open(file_name,'r',encoding='utf-8') as f:
                            content = f.read()
                    else:
                        with open(file_name,'r') as f:
                            content = f.read()
                    self.used_ModuleNames = {}
                    ast_ = ast.parse(content)
                    self.visit(ast_)
                except Exception as e:  
                    pass
    
    def norm(self,s):
        import re
        return re.sub(r'[_|\-]','',s.lower())  

    def processTwo(self):
        
        '''
        filter within-project modules and normal folder name
        '''        
        normal_words = ['test','tests','lib','libs','external','util','exmple','examples','license','utils','docs','doc','bulid','foo']
        
        for name in [n for n in self.abs_imports if n]:
            
            Abspath, Module =  name.rsplit('\\',1) #
            if os.path.join(Abspath,Module.replace('.','\\')) in self.candidates:   #Within modules
                pass
            elif self.norm(Module.split('.')[0]) in self.distribute_names:  #submodules in the project
                pass
            elif self.norm(Module.split('.')[0]) in normal_words:
                pass
            else:
                self.Third_parties[Module] =  self.Import_APIs[Module]              

    def visit_Import(self,node):
        '''
        import A.a.b  is parsed A.a.b
        '''
        for subnode in node.names:
            if subnode.name:
                pkg = subnode.name.split('.',1)[0]
                if pkg not in self.stardard_libs:
                    self.abs_imports.add(self.prefix+subnode.name)
                    alias_name = subnode.asname if subnode.asname else subnode.name 
                    self.used_ModuleNames[alias_name] = subnode.name
                    temp_API = Import_API(module = subnode.name,API_name='None',lineno=str(node.lineno),filepath=self.filepath)
                    self.Import_APIs[subnode.name].append(temp_API.__dict__)  



    def visit_ImportFrom(self,node):
        '''
        remove the import statement: from . import A
        from A import a.b is parsed as A, a.b

        '''
        if node.module:
            if node.level == 0:
                pkg = node.module
                modules = node.names
                if pkg not in self.stardard_libs:
                    self.abs_imports.add(self.prefix+node.module)
                    for subnode in modules:  
                        alias_name = subnode.asname if subnode.asname else subnode.name 
                        self.used_ModuleNames[alias_name] = pkg + '@'+ subnode.name
                        temp_API = Import_API(module = pkg,API_name=subnode.name,lineno=str(node.lineno),filepath=self.filepath)
                        self.Import_APIs[pkg].append(temp_API.__dict__)  

            
    def get_node_name(self,ast_node):
        if isinstance(ast_node,ast.Attribute):
            full_attrName = [ast_node.attr]
            now_attrName = ast_node.value
            while isinstance(now_attrName,ast.Attribute):
                full_attrName.append(now_attrName.attr)
                now_attrName = now_attrName.value
            if isinstance(now_attrName,ast.Name):
                full_attrName.append(now_attrName.id)
            full_attrName = reversed(full_attrName)
            return '.'.join(full_attrName)
        if isinstance(ast_node,ast.Name):
            return ast_node.id 
        return None
  

    def visit_Call(self,node):
        full_name = self.get_node_name(node.func)
       
        if full_name == 'setup' or full_name == 'setuptools.setup':  
            for arg in node.keywords:
                if arg.arg == 'name':
                    if isinstance(arg.value,ast.Str):
                        self.distribute_names.add(self.norm(arg.value.s)) 
        
        lineno = node.lineno
        if full_name == None: 
            return
        for module_name in self.used_ModuleNames:
            for i in range(len(module_name.split('.'))):
                if full_name.split('.')[i] != module_name.split('.')[i]:
                    break     
            else:   
                key_module = self.used_ModuleNames[module_name].split('@')[0]
                API_name = self.used_ModuleNames[module_name] + full_name.replace(module_name,'')
                temp_API = Import_API(module = key_module,API_name=API_name,lineno=str(lineno),filepath=self.filepath)
                self.Import_APIs[key_module].append(temp_API.__dict__)  
                break


def exeute_APIvisitor(path=None):
    # APIs = APIvisitor(proname,path)
    # return APIs.Third_parties
    if path == None:
        return
    
    APIs = APIvisitor(path)
    print(json.dumps(APIs.Third_parties))
        

if __name__ == '__main__':
    path = sys.argv[1]
    exeute_APIvisitor(path)

# test
# Python 2

# Python 3