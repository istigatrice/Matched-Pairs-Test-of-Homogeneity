import numpy as np
import itertools as ite
from scipy.stats import chi2
from scipy.stats import binom_test
import scipy as sp
from Bio.Nexus import Nexus
from Bio import AlignIO
import pandas as pd
from pathlib import Path
import math
import time #only using time for timing/troubleshooting

#import scipy.stats as sp
def nCr(n,r):
    '''Factorial function by Mark Tolonen
    From: http://stackoverflow.com/questions/4941753/is-there-a-math-ncr-function-in-python
    
    '''
    f = math.factorial
    return f(n) // f(r) // f(n-r)

def simMtx(a, x, y):
    '''
    inputs: a = alphabet (e.g. base pairs - 'ACGT')
    x = sequence 1
    y = sequence 2
    
    Thanks Daniel Forsman for improvements:
    http://stackoverflow.com/questions/43511674/calculating-a-similarity-difference-matrix-from-equal-length-strings-in-python/43513055#43513055
    '''
    a = np.array(list(a))
    x = np.array(list(x))
    y = np.array(list(y))
    ax = (x[:, None] == a[None, :]).astype(int)
    ay = (y[:, None] == a[None, :]).astype(int)
    return np.dot(ay.T, ax)

def MPTS(m):
    '''
    inputs: matrix of differences
    outputs: MPTS test statistic
    
    Does the matched pairs test of symmetry
    
    Thanks  Miriam Farber for improvements:
    http://stackoverflow.com/questions/43530744/sum-of-absolute-off-diagonal-differences-in-numpy-matrix/43530874?noredirect=1#comment74114344_43530874
    '''
    d=(m+m.T)
    off_diag_indices=np.triu_indices(len(d),1)
    if 0 in d[off_diag_indices]:
        return float('NaN')
    else:
        numerator=(m-m.T)**2
        denominator=m+m.T
        return np.sum(numerator[off_diag_indices]/denominator[off_diag_indices])

def MPTMS(m):
    """ inputs
            m: a 4x4 matrix of proportions
        outputs
            p: is a p-value for the matched pairs test of marginal symmetry
    """
    r = np.zeros((3))
    r[0]=np.sum(m[0])
    r[1]=np.sum(m[1])
    r[2]=np.sum(m[2])
    c = [sum(row[i] for row in m) for i in range(len(m[0]))]
    d = [r[0]-c[0],r[1]-c[1],r[2]-c[2]]
    ut = np.array([[d[0],d[1],d[2]]])
    u = ut.transpose()
    V = np.zeros((3,3))
    for (i,j) in ite.product(range(0,3),range(0,3)):
        if i==j:
            V[i,j]=r[i]+c[i]+2*m[i][i] #d_{i*}+d{*i}+2d{ii}
        elif i!=j:
            V[i,j]=-(m[i,j]+m[j,i])
    if sp.linalg.det(V) == 0:
        s=float('NaN')
    else:
        Vi=np.linalg.inv(V)
        s = (ut.dot(Vi)).dot(u)[0][0]
    return s

def MPTIS(MPTSs,MPTMSs):
    if isinstance(MPTSs,float) and isinstance(MPTMSs,float)==True:
        s = MPTSs-MPTMSs
    else:
        s=float('NaN')
    return s

def pval(sval,v):
    '''
    Gets a test statistic and outputs a pvalue for a chi squarred test with degrees of freedom v
    '''
    if sval!=float('NaN'):
        p=1.-float(chi2.cdf(sval,v))
    else:
        p=float('NaN')
    return p

def Test_aln(aln,dset,dat):
    """
    needs packages:
    import numpy as np
    import itertools as ite
    from scipy.stats import chi2
    import scipy as sp
    from Bio.Nexus import Nexus
    from Bio import AlignIO
    from pathlib import Path
    import math    
        inputs 
            charset_aln = alignment array of sites
        output
            p = array containing pvalues
    
    """
    aln_array = np.array([list(rec) for rec in aln], np.character)
    dat.charsets.keys() #these are the names to the CHARSETS in the .nex file, which you can iterate over in a for loop
    i = 1
    #no = 946 (44 choose 2)* 3(no. tests) * 9 (no. of charsets)+1 for indexing
    no = nCr(len(aln),2)*3*len([len(v) for v in dat.charsets.keys()])+1
    p=np.empty([no,6],dtype='U21')
    p[0] = np.array(['Dataset','Charset','Test','Sp1','Sp2','p-value'])
    for n in dat.charsets.keys():
        for q in ite.combinations(list(range(len(aln))),2): #iterating over all taxa for sites
            m = simMtx('ACGT',aln_array[:,dat.charsets[n]][q[0]].tostring().upper().decode(),aln_array[:,dat.charsets[n]][q[1]].tostring().upper().decode())
            p[i]=np.array([dset,n,'MPTS',aln[q[0]].name,aln[q[1]].name, pval(MPTS(m),6)])
            i = i+1
            p[i]=np.array([dset,n,'MPTMS',aln[q[0]].name,aln[q[1]].name,pval(MPTMS(m),3)])
            i = i+1
            p[i]=np.array([dset,n,'MPTIS',aln[q[0]].name,aln[q[1]].name,pval(MPTIS(MPTS(m),MPTMS(m)),3)])
            i = i+1
    return p
def plot(p):
    '''
    inputs: p
    outputs: plot of pvalues for each test (hopefully)
    '''
    p[1:,5::3].astype('float64')
    return
def table(p):
    '''
    inputs: matrix of pvalues from Test_aln
    outputs: a summary table
    note: returns 'invalid value encountered in greater_equal' for 'nan' values but this does not affect the summary
    '''
    T=np.empty([len(dat.charsets.keys())*3+1,6], dtype='<U21')
    T[0]= np.array(['Charset','Test','p<0.05','p>=0.05','NA','p_binomial'])
    i = 1
    for n in dat.charsets.keys():
        dfx=df.groupby(['Charset']).get_group(n)
        MPTS = dfx.groupby(['Test']).get_group('MPTS')
        MPTIS = dfx.groupby(['Test']).get_group('MPTIS')
        MPTMS = dfx.groupby(['Test']).get_group('MPTMS')
        T[i][0]=n
        T[i][1]='MPTS'
        T[i][2]=len(np.where(MPTS[MPTS.columns[5]].values.astype(float)<0.05)[0])
        T[i][3]=len(np.where(MPTS[MPTS.columns[5]].values.astype(float)>=0.05)[0])
        T[i][4]=float(len(MPTS))-(float(T[i][2])+float(T[i][3]))
        T[i][5]=binom_test(int(T[i][2]),n=(int(T[i][2])+int(T[i][3])),p=0.05)
        i = i+1
        T[i][0]=n
        T[i][1]='MPTIS'
        T[i][2]=len(np.where(MPTIS[MPTIS.columns[5]].values.astype(float)<0.05)[0])
        T[i][3]=len(np.where(MPTIS[MPTIS.columns[5]].values.astype(float)>=0.05)[0])
        T[i][4]=float(len(MPTIS))-(float(T[i][2])+float(T[i][3]))
        T[i][5]=binom_test(int(T[i][2]),n=(int(T[i][2])+int(T[i][3])),p=0.05)
        i = i+1
        T[i][0]=n
        T[i][1]='MPTMS'
        T[i][2]=len(np.where(MPTMS[MPTMS.columns[5]].values.astype(float)<0.05)[0])
        T[i][3]=len(np.where(MPTMS[MPTMS.columns[5]].values.astype(float)>=0.05)[0])
        T[i][4]=float(len(MPTMS))-(float(T[i][2])+float(T[i][3]))
        T[i][5]=binom_test(int(T[i][2]),n=(int(T[i][2])+int(T[i][3])),p=0.05)
        i = i+1
    #MPTS = df.groupby(['Test']).get_group('MPTS')
    #MPTMS = df.groupby(['Test']).get_group('MPTMS')
    #MPTIS = df.groupby(['Test']).get_group('MPTIS')
    return T
if __name__ == '__main__': 
    aln_path = input('input nex file here:')
    start_time = time.time()
    dset=Path(aln_path).parts[-2]
    dat = Nexus.Nexus()

    dat.read(aln_path)
    
    aln = AlignIO.read(open(aln_path), "nexus")
    p = Test_aln(aln,dset,dat)
    df =pd.DataFrame(p[1:], columns=p[0])
    #df1 = df.groupby('Test')
    #df = pd.DataFrame(p)
    df.to_csv("dataALT.csv")
    table=pd.DataFrame(table(p)[1:],columns=table(p)[0])
    table.to_csv('table.csv')
    print('process complete with no errors in', (time.time() - start_time))