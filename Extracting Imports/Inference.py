# -*- coding:utf-8 -*-

import re
import os
import sys
from collections import defaultdict
import subprocess
import json

from attr import attr


class CrossNode(object):
    def __init__(self,module='None',pkg='None',pos1=0,pos2=0,posall=0,Tpkg='None'):
        self.Module = module
        self.Candidates = 'None'
        self.UniquePkg = pkg
        self.PosAttribute = pos1
        self.PosName = pos2
        self.PosAll = posall
        self.TruePkg = Tpkg
    
    def __lt__(self,other):
        return self.PosAll < other.PosAll
    
    def __eq__(self,other):
        if self.__dict__ == other.__dict__:
            return True
        else:
            return False
    

def get_name_import(path):

    name_imports = []
    walk = os.walk(path, followlinks=True)
    for root, dirs, files in walk:
        files = [fn for fn in files if os.path.splitext(fn)[1] == ".py" ]   
        if len(files) > 0:  
            if path == root:
                name_imports.append(os.path.basename(root))  
            else:
                name_imports.append(os.path.basename(root))
            name_imports += [os.path.splitext(fn)[0] for fn in files]  

    return name_imports

def simcos(s1,s2):
    m=[[0 for i in range(len(s2)+1)] for j in range(len(s1)+1)]
    mmax=0 
    p=0 
    for i in range(len(s1)):
        for j in range(len(s2)):
            if s1[i]==s2[j]:
                m[i+1][j+1]=m[i][j]+1
                if m[i+1][j+1]>mmax:
                    mmax=m[i+1][j+1]
                    p=i+1
    return s1[p-mmax:p]

def split_connect_lower(pkg_name):          
    new_name = pkg_name.lower()
    new_name = re.sub(r'[_|\-]','-',new_name) 
    return new_name

def split_connect_lower_attr(pkg_name):          
    new_name = pkg_name.lower()
    new_name = re.sub(r'[_|\-|.]','',new_name) 
    return new_name


class inference(object):
    def __init__(self,path,tofile):
        self.pypi_packags = self.read_pypi_packages()
        self.pypi_map = self.read_pypi_map()
        self.path = path
        self.tofile= tofile
        
    def read_pypi_packages(self):
        with open('pypi_packages_normal.txt','r') as f:  #Python packages in PyPI
            pypi_packags = {x.strip() for x in f.readlines()}
        return pypi_packags
    def read_pypi_map(self):    
        pypi_map = {}
        with open("unique_map.csv", "r") as f:
            for x in f.readlines():
                temp_map = x.strip().split(',')
                if temp_map[0] not in pypi_map:
                    pypi_map[temp_map[0]] = []
                if temp_map[1] not in pypi_map[temp_map[0]]:
                    pypi_map[temp_map[0]].append(temp_map[1])
        return pypi_map


    def parse_imports(self,path):
        parse_imports = {'Python2': None, 'Python3': None}

        # Python 2
        child = subprocess.Popen('D:\Python2.7\python.exe API_visiter.py {}'.format(path), stdout=subprocess.PIPE)
        logs = child.stdout.read()
        try:
            parse_imports['Python2'] = json.loads(logs)
            print('Parsing result in Python 2')
        except json.JSONDecodeError:
            print('Parsing result error in Python2')
        
        # Python3
        child = subprocess.Popen('python3 API_visiter.py {}'.format(path), stdout=subprocess.PIPE)
        logs = child.stdout.read()
        try:
            parse_imports['Python3'] = json.loads(logs)
            print('Parsing result in Python 3')
        except json.JSONDecodeError:
            # print(logs)
            print('Parsing result error in Python3')
        
        return parse_imports


    def nameResolve(self,attrs):
        resolve_pkg = set() 
        parent_pkg = attrs.split('.')[0]
        if parent_pkg in ('test','tests','util','exmple','examples','license','utils','docs','doc'):
            return list(resolve_pkg)
        
        if len(attrs.split('.')) == 1:   
                new_parent_pkg =  split_connect_lower(parent_pkg) 
                if new_parent_pkg in self.pypi_packags:
                    resolve_pkg =[new_parent_pkg] 
        else:
            key_word = attrs.split('.') 
            candidate_pkg = []
            for i in range(len(key_word)):  
                candidate_pkg.append('.'.join(key_word[0:i+1])) 
            most_consistent_len = 0
            for cp in candidate_pkg:
                new_cp = split_connect_lower(cp)
                if  new_cp in self.pypi_packags:
                    # resolve_pkg.add(new_cp)
                    if most_consistent_len < len(new_cp.split('.')):
                        resolve_pkg = {new_cp}
                    elif most_consistent_len == len(new_cp.split('.')):
                        resolve_pkg.add(new_cp)
                    else:
                        pass
        
        return list(resolve_pkg)

    def get_pkg_names(self,import_modules):
        result = {}
        for im in import_modules:
            parent_pkg = im.split('.')[0]
            if parent_pkg in self.pypi_map and parent_pkg not in ('test','tests','util','exmple','examples','license','utils','docs','doc'):
                result[im] = self.pypi_map[parent_pkg]
            else:
                # top modules and submodules
                result_im = []
                for k in self.pypi_map:
                    if '@' in k and parent_pkg not in ('test','tests','util','exmple','examples','license','utils','docs','doc'):
                        if parent_pkg in k.split('@'):
                            result_im += self.pypi_map[k] 
                    
                result[im] = result_im 

        return result


    def infer(self,name_imports,Third_parties,ignore=None):

        packages = self.get_pkg_names(Third_parties)    
        Has_identities = {} 
        Final_Nodes = []
        for attrs,map_pkg in packages.items():
            unipkgs = set(map_pkg)
            if ignore and attrs in ignore:  
                continue
            true_dep = set()
            Candidate_Nodes = []
            Final_Node = CrossNode(module=attrs)
            pypi_found = self.nameResolve(attrs)
                    
            if len(unipkgs) == 1:
                Final_Node.UniquePkg = map_pkg[0]   
            elif len(unipkgs) == 0:
                Final_Node.UniquePkg = 'None'
            else:     
            
                normalize_im = split_connect_lower_attr(attrs)
                
                for pkg in unipkgs:
                    normalize_pkg = split_connect_lower_attr(pkg)
                    pos2 = 2*len(simcos(normalize_im,normalize_pkg)) / (len(normalize_im) + len(normalize_pkg))  
                    new_node = CrossNode(module=attrs,pkg=pkg)
                    new_node.PosName = pos2
                    new_node.PosAll = pos2 
                    Candidate_Nodes.append(new_node)
                if attrs.split('.')[0] in Has_identities:
                    Candidate_Nodes.append(CrossNode(module=attrs,pkg=Has_identities[attrs.split('.')[0]]))
                Candidate_Nodes.sort(reverse=True)  
                if len(Candidate_Nodes) > 0:   
                    max_pos = Candidate_Nodes[0].PosAll  
                    if len(Candidate_Nodes) < 5:  
                        Final_Node = Candidate_Nodes[0]
                        Has_identities[attrs.split('.')[0]] = Candidate_Nodes[0].UniquePkg
                    else:   
                        threshold = 0.5
                        if max_pos > threshold:
                            Final_Node = Candidate_Nodes[0]
                            Has_identities[attrs.split('.')[0]] = Candidate_Nodes[0].UniquePkg
                    if len(Candidate_Nodes) > 5:
                        Final_Node.Candidates = '@'.join([item.UniquePkg for item in Candidate_Nodes[0:5]])
                    else:
                        Final_Node.Candidates = '@'.join([item.UniquePkg for item in Candidate_Nodes])   #

            if Final_Node.UniquePkg == 'None':   
                if pypi_found and len(pypi_found) == 1:  
                    Final_Node.UniquePkg = pypi_found[0]  
                    if attrs.split('.')[0] in name_imports:
                        Final_Node.UniquePkg = pypi_found[0]+'#'+'Within'  
                    else:
                        print(attrs,pypi_found[0])
                        Final_Node.UniquePkg = pypi_found[0]
                    
                elif attrs.split('.')[0] in name_imports:
                    Final_Node.UniquePkg= 'Within'
                else:
                    Final_Node.UniquePkg = 'Unknown'
            
            if len(true_dep) == 0:
                Final_Node.TruePkg = 'None'
            else:
                Final_Node.TruePkg = '@'.join(true_dep)
            Final_Nodes.append(Final_Node.__dict__) 
        return Final_Nodes

    def run_inference(self):
        parse_result = self.parse_imports(self.path)
        Third_parties = set()
        for item in parse_result:
            if parse_result[item]:
                Third_parties = Third_parties | set(parse_result[item].keys())

        name_imports = get_name_import(self.path)
        Final_nodes = self.infer(name_imports,Third_parties)

        cross_to_files = set()
        for v in Final_nodes:
            pkg = v['UniquePkg']
            if  'Unknown' != pkg and 'Within' != pkg:
                cross_to_files.add(pkg)
        
        with open(self.tofile,'w',encoding='utf-8') as f:
            f.write('\n'.join(cross_to_files))

if __name__ == '__main__':
    # input: the local path of a project
    # example : E:\\pro\\faker
    path = sys.argv[1]  
    tofile = sys.argv[2]
    infer_node = inference(path,tofile)
    infer_node.run_inference()
    