

#################################################
# Identifying declarative dependency declaration
'''
DDD1 :d==c1 {d,c1}
DDD2 :d==c1;systemc2 {d, c1}_systemc2 
DDD3 :git+url#egg=d  {d,*} 
DDD4 :local project path/url {GetDepFromUrl(url)}
DDD5 :arg url  {GetDepFromUrl(url)}
'''
import os
import ast,re
import pandas as pd
import astunparse
import toml
# import json

class DepsStatement(): 
    def __init__(self,file_name):
        self.all_deps = set()
        if os.path.splitext(os.path.basename(file_name))[1]== '.txt': 
            self.process_deps(file_name)    
        elif os.path.basename(file_name) == 'Pipfile' : 
            self.toml_parse(file_name,['packages','dev-packages']) 
        # elif os.path.splitext(os.path.basename(file_name))[1] in ('.in','.toml','.json'):  #supporting other formats of configuration files in the future
            # self.json_parse(file_name,[])  
            # self.toml_parse(file_name,[])  
        
        else:
            return 
        
    def toml_parse(self,file_name, parameter_list): 
        content = toml.load(file_name)
        for parameter in parameter_list:
            for name,version in content[parameter].items():
                if isinstance(version,ast.Str):
                    self.all_deps.add(name+'=='+version)
                else:
                    self.all_deps.add(name+'==*')

    # def json_parse(self,file_name, parameter_list): 
    #     content = json.load(file_name)
    #     for parameter in parameter_list:
    #         for name,additional in content[parameter].items():
    #             if 'version' in additional:
    #                 self.all_deps.add(name+'=='+additional['version'])
    #             else:
    #                 self.all_deps.add(name+'==*')
                
    def process_deps(self,file_name):

        try:
            with open(file_name,'r',encoding='utf-8') as f:
                content = f.readlines()
        except Exception: 
            print(file_name) 
            return
        require_pattern = re.compile(r'[\w|_|]+\s*[>|<|^|~|=]?\s*=?\s*(.*)?')         
        describe_pattern = re.compile(r'\[[\w|_|\s]+\]')          
        
        for line in content:
            line = line.strip()
            if line.startswith('#'):     
                pass
            elif line.startswith('-r') or line.startswith('--requirement'):  #-r ,file
                pass
            elif line.startswith('-e') or line.startswith('--editable'): #-e
                if len(line.split()) > 1:
                    self.ifvalid(line.split()[1],'B.11')                
            elif line.startswith('-i') or line.startswith('--index-url'): #-i,--index-url
                if len(line.split()) > 1:
                    self.ifvalid(line.split()[1],'B.11')
            elif line.startswith('-f') or line.startswith('--find-links'):
                if len(line.split()) > 1:
                    self.ifvalid(line.split()[1],'B.11')
            elif os.path.exists(line): 
                pass
            elif require_pattern.match(line):
                self.ifvalid(line,'')
            elif describe_pattern.match(line):
                pass
            else:
                pass
    def ifvalid(self,line,postfix):
        if os.path.exists(line):
            return
        if line.startswith('"') and line.endswith('"'):
            line = line.strip('"')
        if line.startswith("'") and line.endswith("'"):
            line = line.strip("'")

        if line.startswith('git+') or line.startswith('git:'):
            PN,version= self.GetDepFromUrl(line)
            if PN != '*':
                if version == '*':
                    self.all_deps.add(PN+';special#B.9 '+postfix)  
                else:
                    self.all_deps.add(PN+'=='+version + ';special#B.9' )
        elif line.startswith('http:') or line.startswith('https:'):
            PN,version= self.GetDepFromUrl(line)
            if PN != '*':
             
                if version == '*':
                    self.all_deps.add(PN+';special#B.10 ' + postfix )
                else:
                    self.all_deps.add(PN+'=='+version + ';special#B.10 ' + postfix)
        else:
            other_deps = line.split('#')[0]   
            self.all_deps.add(other_deps)
        
      
    def GetDepFromUrl(self,url_dep): 
        project_name = re.search(r'#egg=(?P<PN>[^\s]*)',url_dep)  
        if project_name:
            PN = project_name.group('PN')
            a = re.search(r'//(?P<repo>.*)#',url_dep)
            repo = a.group('repo')
            version = '*'
            if '@' in repo:  
                version = repo.split('@')[1]
            return PN,version
        else:
            project_name = re.search(r'github.com/(?P<PN>[^\s].*)',url_dep)  
            if project_name:
                repo = project_name.group('PN')
                version = '*'
                if '@' in repo:
                    version = repo.split('@')[1]
                PN = repo.split('@')[0].split('/')[1]
                PN = PN.replace('.git','')  
                PN = PN.replace('.tar.gz','')  
                return PN,version
            else:
                return '*','*'

##############################################
# Identifying imperative dependency declaration

class dflow(object): 
    def __init__(self,from_,to_,condition='*',status='str',extra_info='*'):
        if from_ == to_:
            self.from_ = '*'
        else:
            self.from_ = from_
        self.to_ = to_
        self.condition = condition
        self.status = status
        self.extra_info = extra_info  

class DepsVisitor(ast.NodeVisitor): 
    def __init__(self,file_name):
        self.file_name = file_name
        
        self.flag_finish = 0
        self.keywords = ['install_requires','tests_require','setup_requires','extras_require']
        with open(file_name, "r", encoding='utf-8') as f:
            contents = f.read()
            for key  in  self.keywords:
                if key in contents:
                    break
            else:
                return None
        self.nodes = {}
        self.UnresolvedNames = [] 
        self.ResolvedNames = []  
        self.flag_mamual = 0
        self.statements = 0   
        self.flag_args = 0
        self.deps = {}
        self.dataflow = []
        self.scope_If = []
       
        for a  in  self.keywords:
            self.deps[a] = []
            self.UnresolvedNames.append('original@'+a)  
        try:
            self.process(file_name)
        except Exception as e:
            print(file_name)
            print(e)
            return
        
        self.merge_df()

    
    def merge_df(self): 
        keywords = ['install_requires','tests_require','setup_requires','extras_require','original']
        end_dataflow = []
        def search(dfs,to,c):
            ret_df = []
            for df in dfs:
                if to == df.from_:
                    if df.status == 'str':
                        if c =='*': 
                            ret_df.append({'df':df,'c':df.condition})
                        else:
                            ret_df.append({'df':df,'c':c+'@'+df.condition})
                    else:
                        if c == '*': 
                            ret_df += search(dfs,df.to_,df.condition)
                        else:
                            ret_df += search(dfs,df.to_,c+'@'+df.condition)
            return ret_df
        remove_dataflow = [] 
        for df in self.dataflow:
            if df.from_ == '*': 
                pass
            else:
                remove_dataflow.append(df)
                
        for df in remove_dataflow:
            if df.from_ == '*': 
                continue
            if df.from_ in keywords:
                if df.status == 'str':
                    end_dataflow.append(df)
                elif df.status == 'file':
                    end_dataflow.append(df)
                    
                else:
                    df_s = search(remove_dataflow,df.to_,df.condition)
                    for df_ in df_s:
                        if df_['df'].status == 'str': 
                            end_dataflow.append(dflow(from_=df.from_,to_=df_['df'].to_,condition=df_['c'],status='str'))
        
        self.end_dataflow = end_dataflow
            

    def process(self,file_name):
        self.remove_nodes = set()
        
        self.process_deps(file_name)
        
        for rm_n in self.remove_nodes:     
            self.UnresolvedNames.remove(rm_n)

        if self.flag_args == 1:  #entering setup()
            for a  in  self.keywords:
                self.UnresolvedNames.remove('original@'+a)   
        TobeRemoved = self.UnresolvedNames.copy()
        while 1:
            self.remove_nodes = set()
            self.process_deps(file_name)
           
            for rm_n in self.remove_nodes:     
                self.UnresolvedNames.remove(rm_n)
            #
            if len(self.UnresolvedNames) == 0 or (set(TobeRemoved) == set(self.UnresolvedNames)):   
                TobeRemoved = self.UnresolvedNames.copy()
                break
            else:
                TobeRemoved = self.UnresolvedNames.copy()
        
        if len(TobeRemoved) > 0: 
            pass
           
      
    def process_deps(self,file_name):
        try:
            with open(file_name, "rt", encoding='utf-8') as f:
                contents = f.read()
        except Exception as e:
            # use 2to3.py to transfer Python2 to Python3
            print('use 2to3.py to transfer Python2 to Python3')
            os.system('python3 2to3.py -w {}'.format(file_name))   
            with open(file_name, "rt", encoding='utf-8') as f:
                contents = f.read()
            
        self.visit(ast.parse(contents))
        self.flag_finish = 1
        

    def process_resolved(self,file_name):  
        with open(file_name, "rt", encoding='utf-8') as f:
            contents = f.read()
        self.visit(ast.parse(contents))
       
    
        
    def isfile(self,arg):
        if isinstance(arg,ast.Str):
            pass
        else:
            return False
        candidate_file = os.path.splitext(os.path.basename(arg.s))
        if candidate_file[1] in ('.txt','.in','.pip','.toml','.rst'):
            return True
        return False

    def assgin(self,value,from_scope,c='*'):
        if isinstance(value,ast.Str):  
            self.dataflow.append(dflow(from_=from_scope,to_=value.s,condition=c))
        elif isinstance(value,ast.Name):  
            self.dataflow.append(dflow(from_=from_scope,to_=value.id,status='name',condition=c))
            if value.id in self.ResolvedNames:
                pass
               
            else:
                self.UnresolvedNames.append(from_scope+'@'+value.id)  
        elif isinstance(value,ast.List) or isinstance(value,ast.Tuple): #list or tuple
            deps_list = value.elts
          
            for dep in deps_list:
                if isinstance(dep,ast.Str):
                   
                    self.dataflow.append(dflow(from_=from_scope,to_=dep.s,condition=c))
                
                else:
                    self.assgin(dep,from_scope,c)
        elif isinstance(value,ast.Dict):  
           
            keys = value.keys
            values = value.values 
            for i in range(len(keys)):
                self.assgin(values[i],from_scope)

        
        elif isinstance(value,ast.Subscript):
            if isinstance(value.value,ast.Name):
                self.dataflow.append(dflow(from_= from_scope,to_=value.value.id,status='name',condition=c)) 
                if value.value.id in self.ResolvedNames:
                    pass
                else:
                    self.UnresolvedNames.append(from_scope+'@'+value.value.id)# 
            elif isinstance(value.value,ast.Attribute):  #A.B['sub']
                self.assgin(value.value.value,from_scope,c)
            elif isinstance(value.value,ast.Subscript):   ##A['sub1]['sub2']
                self.assgin(value.value.value,from_scope,c)

        elif isinstance(value,ast.BinOp): #
            left_expr = value.left
            right_expr = value.right
            if isinstance(value.op,ast.Add):  

                self.assgin(left_expr,from_scope)  
                self.dataflow.append(dflow(from_=from_scope,to_=from_scope,status='name',condition=c))
                self.assgin(right_expr,from_scope)
                self.dataflow.append(dflow(from_=from_scope,to_=from_scope,status='name',condition=c))
        
        elif isinstance(value,ast.IfExp): #if
            self.assgin(value.body,from_scope+'_if')
            self.dataflow.append(dflow(from_= from_scope,to_=from_scope+'_if',status='name',condition=c+'@'+astunparse.unparse(value.test).strip()))
            self.assgin(value.orelse,from_scope+'_orelse')
            self.dataflow.append(dflow(from_= from_scope,to_=from_scope+'_orelse',status='name',condition=c+'@'+"not "+astunparse.unparse(value.test).strip()))  

        elif isinstance(value,ast.Call): 
           
            if isinstance(value.func,ast.Name):   
                if value.func.id == 'dict':
                    for kw in value.keywords: 
                        self.assgin(kw.value,self.scope,c)

            for arg in value.args: 
                if isinstance(arg,ast.List) or isinstance(arg,ast.Tuple): 
                    for arg_l in arg.elts:
                        if isinstance(arg_l,ast.Str) and self.isfile(arg):
                            self.dataflow.append(dflow(from_= from_scope,to_=arg.s,status='file',condition=c))  

                elif isinstance(arg,ast.Str) and self.isfile(arg):
                    self.dataflow.append(dflow(from_= from_scope,to_=arg.s,status='file',condition=c)) 

                else:
                    self.assgin(arg,from_scope,c)

            if isinstance(value.func,ast.Name):   #read_file('a')
                    self.dataflow.append(dflow(from_=from_scope,to_=value.func.id,status='func',condition=c))
                    if value.func.id in self.ResolvedNames:
                        pass
                    else:
                        self.UnresolvedNames.append(from_scope+'@'+value.func.id)

            elif isinstance(value.func,ast.Attribute): #read_file('a').split() 
                self.assgin(value.func.value,from_scope,c)
        else:
            pass


    def visit_Module(self, node):
        self.generic_visit(node)
    
    def visit_If(self,node):  
        
        self.scope_If.append(astunparse.unparse(node.test).strip())
        for smt in node.body:
            self.visit(smt)
        self.scope_If.pop()

        self.scope_If.append('not '+astunparse.unparse(node.test).strip())
        for smt in node.orelse:
            self.visit(smt)
        self.scope_If.pop()

    def visit_FunctionDef(self, node):
        # update return value if I can
        for arg in node.args.args:
            self.visit(arg)
        for d in node.args.defaults:
            self.visit(d)
        for smt in node.decorator_list:
            self.visit(smt) 
        for smt in node.body:
            self.visit(smt)  
       
            if self.flag_finish > 0:  
                if isinstance(smt,ast.Return):
                    
                    for it in self.UnresolvedNames:
                        if it.split('@')[1] == node.name:   
                            self.scope = it.split('@')[0]  
                            self.assgin(smt.value,self.scope)     
                            

    def visit_Assign(self,node):
        if self.flag_finish > 0:  
            if len(node.targets) == 1:  
                tar = node.targets[0]
                if isinstance(tar,ast.Name): # a = xx
                    
                    for it in self.UnresolvedNames:
                        if it.split('@')[1] == tar.id:   
                            self.scope = it.split('@')[0] 
                            self.assgin(node.value,self.scope)
                            self.remove_nodes.add(it)
                            self.ResolvedNames.append(it.split('@')[1])
                if isinstance(tar,ast.Subscript): # a['sub'] = xx
                    if isinstance(tar.value,ast.Name):  # a['sub'] = xx
                        for it in self.UnresolvedNames:
                            if it.split('@')[1] == tar.value.id:   
                                self.scope = it.split('@')[0]  
                                self.assgin(node.value,self.scope)
                                self.remove_nodes.add(it)
                                self.ResolvedNames.append(it.split('@')[1]) 
                        if isinstance(tar.slice,ast.Index):  #a['install_requires'] = xx 
                            if isinstance(tar.slice.value,ast.Str):  
                                if tar.slice.value.s in self.keywords:
                                    self.scope = tar.slice.value.s  
                                    if isinstance(node.value,ast.Dict):    
                                        keys = node.value.keys
                                        values = node.value.values 
                                        for i in range(len(keys)):
                                            self.assgin(values[i],self.scope,'@'.join(self.scope_If))
                                    else:
                                        self.assgin(node.value,self.scope,'@'.join(self.scope_If))
                                    
                    elif isinstance(tar.value,ast.Subscript):   ##A['sub1]['sub2'] = xx
                        if isinstance(tar.value.value,ast.Name):  
                            for it in self.UnresolvedNames:
                                if it.split('@')[1] == tar.value.value.id:   
                                    self.scope = it.split('@')[0]  
                                    self.assgin(node.value,self.scope)
                                    self.remove_nodes.add(it)
                                    self.ResolvedNames.append(it.split('@')[1])

                if isinstance(node.value,ast.Call):   #setup_info = dict()  setup(**setup_info)  
                    for kw in node.value.keywords:       
                        if kw.arg  in  self.keywords:
                            self.scope = kw.arg
                            self.from_scope = kw.arg
                            kwValue = kw.value                
                            if isinstance(kwValue,ast.Dict):    
                                keys = kwValue.keys
                                values = kwValue.values 
                                for i in range(len(keys)):
                                    self.assgin(values[i],self.scope,'@'.join(self.scope_If))
                            else:
                                self.assgin(kwValue,self.scope,'@'.join(self.scope_If))

                
                if isinstance(node.value,ast.Dict):   #setup_info = {}  setup(**setup_info)  
                    for i in range(len(node.value.keys)):
                        key = node.value.keys[i]
                        kw = node.value.values[i]
                        if isinstance(key,ast.Str):
                            if key.s in self.keywords:                        
                                self.scope = key.s
                                if isinstance(kw,ast.Dict):   
                                    values = kw.values
                                    for j in range(len(values)):
                                        self.assgin(values[j],self.scope,'@'.join(self.scope_If))
                                else:
                                    self.assgin(kw,self.scope,'@'.join(self.scope_If))
                                
    def visit_Call(self,node):
        if self.flag_finish == 0: 
           
            if isinstance(node.func,ast.Name):   #setup() 
                pass
            elif isinstance(node.func,ast.Attribute): #setuptools.setup()
                pass
           
            for kw in node.keywords:       
                if kw.arg  in  self.keywords:
                    self.scope = kw.arg
                    self.from_scope = kw.arg
                    kwValue = kw.value
                    self.flag_args = 1                  
                    if isinstance(kwValue,ast.Dict):    
                        keys = kwValue.keys
                        values = kwValue.values 
                        for i in range(len(keys)):
                            self.assgin(values[i],self.scope,'@'.join(self.scope_If))
                    else:
                        self.assgin(kwValue,self.scope,'@'.join(self.scope_If))
        
        if self.flag_finish > 0:  
            if isinstance(node.func,ast.Attribute):
                if isinstance(node.func.value,ast.Name): #A.append()
                    if node.func.attr == 'append' or node.func.attr == 'extend': #A.append()；A.extend()
                        for it in self.UnresolvedNames:
                            if node.func.value.id == it.split('@')[1]:  
                                for arg_ in node.args:
                                    self.assgin(arg_,node.func.value.id,'@'.join(self.scope_If))
                    
                    if node.func.attr == 'update': 
                        for it in self.UnresolvedNames:
                            if node.func.value.id == it.split('@')[1]:  
                                for arg_ in node.args:
                                    self.assgin(arg_,node.func.value.id,'@'.join(self.scope_If))



def read_pypi_data():
    with open('pypi_packages_normal.txt','r') as f:
        pypi_data = {x.strip() for x in f}
    
    return pypi_data

pypi_data = read_pypi_data()

import requests
def IsPyPIlibrary(pkg,pypi_server="https://pypi.python.org/pypi/",proxy=None):
    if len(pkg) == 0 or pkg == '.': #empty
        return False
    # query in local resource
    normal_pkg = re.sub(r'[_|\-]','-',pkg.lower()) 
    if normal_pkg in pypi_data:
        return True
    else:
        # query by requests 
        response = requests.get("{0}{1}".format(pypi_server, pkg), proxies=proxy)
        if response.status_code == 200:
            return True
        elif response.status_code >= 300:
            return False
    
    
def Splitdepversion(py_dep):
    dep_name = ''
    version = '*'    
    if len(py_dep.split(';')) > 1:
        py_dep,extra_info = py_dep.split(';',1)   
    else:
        py_dep = py_dep.split(';')[0]
        extra_info = '*'

    py_dep = py_dep.split('#')[0]  
    
    py_dep = py_dep.strip('\\').strip() 
    
    for i,ch in enumerate(py_dep):
        if ch in ('>',"<","^","~","=",'!'): 
            version = str(py_dep[i:])
            break
        else:
            dep_name = dep_name + ch

    # 
    dep_name = dep_name.replace('\"','') 
    dep_name = dep_name.replace('\'','')
    dep_name = dep_name.strip()
    dep_name = dep_name.split('[')[0]  # A[extras]==>A
    #  
    version = version.strip('=').strip() 
    version = version.replace('\"','')   
    version = version.replace('\'','')
    if len(dep_name) == 0:
        return [dep_name,version,extra_info]
        
    if version[0] in ('>',"<","^","~",'!'):
        pass
    else:
        version = '=='+version

    if dep_name == '*':
        dep_name = ''

    return [dep_name,version,extra_info]


def get_config_dep(file_name,tofile):
    alldeps = []
    if os.path.basename(file_name) == 'setup.py':  
        a = DepsVisitor(file_name)
        if a.flag_finish == 0:
            pass
        else:
            tdpes = a.end_dataflow
            for key in tdpes:
                alldeps.append({'dep':key.to_,'filepath':file_name,'type':key.from_,'condition':key.condition,'status':key.status})
    elif os.path.splitext(os.path.basename(file_name))[1]== '.txt': 
        if 'require' in file_name:
            DepsState = DepsStatement(file_name)
            if DepsState.all_deps:
                for dep in DepsState.all_deps:
                    alldeps.append({'dep':dep,'filepath':file_name,'type':'*','condition':'*','status':'*'})

    elif os.path.basename(file_name) == 'Pipfile' :           
        DepsState = DepsStatement(file_name)
        if DepsState.all_deps:
            for dep in DepsState.all_deps:
                alldeps.append({'dep':dep,'filepath':file_name,'type':'*','condition':'*','status':'*'})
    
    final_deps = []
    for item in alldeps:
        if item['status'] != 'file':
            [dep_name,version,extra_info] = Splitdepversion(item['dep'])
            if IsPyPIlibrary(dep_name):
                final_deps.append({'dep':dep_name,'version':version,'filepath':item['filepath'],'type':'*','condition':item['condition']+'@'+extra_info,'status':key.status})

    pd.DataFrame(final_deps).to_csv(tofile)


def get_project_dep(pro_path,tofile=None):
    alldeps = []
    all_files = []

    for root ,dirs,files in os.walk(pro_path):
        for file_now in files:                
            file_name = os.path.join(root,file_now)   
            all_files.append(file_name)
            if file_now == 'setup.py':  
                a = DepsVisitor(file_name)
                if a.flag_finish == 0:
                    continue
                tdpes = a.end_dataflow
                for key in tdpes:
                    alldeps.append({'dep':key.to_,'filepath':file_name,'type':key.from_,'condition':key.condition,'status':key.status})

            if os.path.splitext(os.path.basename(file_name))[1]== '.txt': 
                if 'require' in file_name:
                    DepsState = DepsStatement(file_name) 
                    if DepsState.all_deps:
                        for dep in DepsState.all_deps:
                            alldeps.append({'dep':dep,'filepath':file_name,'type':'*','condition':'*','status':'*'})

            elif os.path.basename(file_name) == 'Pipfile' :           
                    DepsState = DepsStatement(file_name)
                    if DepsState.all_deps:
                        for dep in DepsState.all_deps:
                            alldeps.append({'dep':dep,'filepath':file_name,'type':'*','condition':'*','status':'*'})

    final_deps = []
    for item in alldeps:
        if item['status'] == 'file':
            for fp in all_files:
                if os.path.basename(fp) == item['dep']:  #
                    DepsState = DepsStatement(fp)  
                    if DepsState.all_deps:
                        for dep in DepsState.all_deps:
                            [dep_name,version,extra_info] = Splitdepversion(dep)
                            if IsPyPIlibrary(dep_name):
                                final_deps.append({'dep':dep_name,'version':version,'filepath':item['filepath'],'type':item['type'],'condition':item['condition']+'@'+extra_info,'status':'*'}) 
        else:
            [dep_name,version,extra_info] = Splitdepversion(item['dep'])
            if IsPyPIlibrary(dep_name):
                final_deps.append({'dep':dep_name,'version':version,'filepath':item['filepath'],'type':item['type'],'condition':item['condition']+'@'+extra_info,'status':'*'}) 
    

    project_name = os.path.basename(pro_path)
    if tofile:
        pd.DataFrame(final_deps).to_csv(tofile)
    else:
        pd.DataFrame(final_deps).to_csv('result\\{}_Metadata.csv'.format(project_name))

import sys
def main():
    propath = sys.argv[1]
    tofile = sys.argv[2]

    if os.path.isfile(propath):
        get_config_dep(propath,tofile)
    else:
        get_project_dep(propath,tofile)
        
if __name__ == '__main__':
    main()
