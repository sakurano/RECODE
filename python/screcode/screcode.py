import h5py
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import sklearn.decomposition
import scipy.sparse
import seaborn as sns
import time
import warnings


class RECODE():
    """ add comment
    """

    def __init__(
        self,
        return_param = False,
        acceleration = True,
        acceleration_ell_max = 1000,
        param_estimate = True,
        ell_manual = 10,
    ):
        self.acceleration = acceleration
        self.acceleration_ell_max = acceleration_ell_max
        self.param_estimate=param_estimate
        self.ell_manual=ell_manual
        self.return_param=return_param
    
    def fit(self,X):
        """ Add description here
        Parameters
        ----------
        data: description
        return_param: description

        Returns
        --------
            description
        """
        n,d = X.shape
        if self.acceleration:
            self.n_pca = min(n-1,d-1,self.acceleration_ell_max)
        else:
            self.n_pca = min(n-1,d-1)
        X_svd = X
        n_svd,d = X_svd.shape
        X_mean = np.mean(X,axis=0)
        X_svd_mean = np.mean(X_svd,axis=0)
        svd = sklearn.decomposition.TruncatedSVD(n_components=self.n_pca).fit(X_svd-X_svd_mean)
        SVD_Sv = svd.singular_values_
        self.PCA_Ev = (SVD_Sv**2)/(n_svd-1)
        self.U = svd.components_
        PCA_Ev_sum_all = np.sum(np.var(X,axis=0))
        PCA_Ev_NRM = np.array(self.PCA_Ev,dtype=float)
        PCA_Ev_sum_diff = PCA_Ev_sum_all - np.sum(self.PCA_Ev)
        n_Ev_all = min(n,d)
        for i in range(len(PCA_Ev_NRM)-1):
            PCA_Ev_NRM[i] -= (np.sum(self.PCA_Ev[i+1:])+PCA_Ev_sum_diff)/(n_Ev_all-i-1)
        self.PCA_Ev_NRM = PCA_Ev_NRM
        self.ell_max = np.sum(self.PCA_Ev>1.0e-10)
        self.L = np.diag(np.sqrt(self.PCA_Ev_NRM[:self.ell_max]/self.PCA_Ev[:self.ell_max]))
        self.X = X
        self.X_mean = np.mean(X,axis=0)
        self.PCA_Ev_sum_all = PCA_Ev_sum_all
    
    def noise_reduct_param(
        self,
        delta = 0.05
    ):
        comp = max(np.sum(self.PCA_Ev_NRM>delta*self.PCA_Ev_NRM[0]),3)
        self.ell = min(self.ell_max,comp)
        self.X_RECODE = noise_reductor(self.X,self.L,self.U,self.X_mean,self.ell)
        return self.X_RECODE
        
    def noise_reductor(self,X,L,U,Xmean,ell):
        U_ell = U[:ell,:]
        L_ell = L[:ell,:ell]
        return np.dot(np.dot(np.dot(X-Xmean,U_ell.T),L_ell),U_ell)+Xmean
    
    def noise_reduct_noise_var(
        self,
        noise_var = 1,
        ell_min = 3
    ):
        PCA_Ev_sum_diff = self.PCA_Ev_sum_all - np.sum(self.PCA_Ev)
        PCA_Ev_sum = np.array([np.sum(self.PCA_Ev[i:]) for i in range(self.n_pca)])+PCA_Ev_sum_diff
        d_act = sum(np.var(self.X,axis=0)>0)
        X_var  = np.var(self.X,axis=0)
        dim = np.sum(X_var>0)
        thrshold = (dim-np.arange(self.n_pca))*noise_var
        comp = np.sum(PCA_Ev_sum-thrshold>0)
        self.ell = max(min(self.ell_max,comp),ell_min)
        X_RECODE = self.noise_reductor(self.X,self.L,self.U,self.X_mean,self.ell)
        return X_RECODE
    
    def noise_var_est(
        self,
        X,
        cut_low_exp=1.0e-10,
        out_file='variance'
    ):
        n,d = X.shape
        X_var = np.var(X,axis=0)
        idx_var_p = np.where(X_var>cut_low_exp)[0]
        X_var_sub = X_var[idx_var_p]
        X_var_min = np.min(X_var_sub)-1.0e-10
        X_var_max = np.max(X_var_sub)+1.0e-10
        X_var_range = X_var_max-X_var_min
        
        div_max = 1000
        num_div_max = int(min(0.1*d,div_max))
        error = np.empty(num_div_max)
        for i in range(num_div_max):
                num_div = i+1
                delta = X_var_range/num_div
                k = np.empty([num_div],dtype=int)
                for j in range(num_div):
                    div_min = j*delta+X_var_min
                    div_max = (j+1)*delta+X_var_min
                    k[j] = len(np.where((X_var_sub<div_max) & (X_var_sub>div_min))[0])
                error[i] = (2*np.mean(k)-np.var(k))/delta/delta
        
        opt_div = int(np.argmin(error)+1)

        k = np.empty([opt_div],dtype=int)
        k_index = np.empty([opt_div],dtype=list)
        delta = X_var_range/opt_div
        for j in range(opt_div):
                div_min = j*delta+X_var_min
                div_max = (j+1)*delta+X_var_min
                k[j] = len(np.where((X_var_sub<=div_max) & (X_var_sub>div_min))[0])
        idx_k_max = np.argmax(k)
        div_min = idx_k_max*delta+X_var_min
        div_max = (idx_k_max+1)*delta+X_var_min
        idx_set_k_max = np.where((X_var_sub<div_max) & (X_var_sub>div_min))[0]
        var = np.mean(X_var_sub[idx_set_k_max])
        return var
    
    def fit_transform(self,X):
        self.fit(X)
        if self.param_estimate:
            noise_var = recode_tools.noise_var_est(X)
        else:
            noise_var = 1
        return self.noise_reduct_noise_var(noise_var)
    

class scRECODE():
    def __init__(
        self,
        return_param = False,
        acceleration = True,
        acceleration_ell_max = 1000,
        verbose = True
        ):
        self.return_param = return_param
        self.acceleration = acceleration
        self.acceleration_ell_max = acceleration_ell_max
        self.verbose = verbose

    def noise_variance_stabilizing_normalization(
        self,
        X,
        return_param=False
    ):
        ## scaled X
        X_nUMI = np.sum(X,axis=1)
        X_scaled = (X.T/X_nUMI).T
        X_scaled_mean = np.mean(X_scaled,axis=0)
        ## normalization
        noise_var = np.mean(X.T/X_nUMI/X_nUMI,axis=1)
        noise_var[noise_var==0] = 1
        X_norm = (X_scaled-np.mean(X_scaled,axis=0))/np.sqrt(noise_var)
        self.X_nUMI = X_nUMI
        self.X_scaled = X_scaled
        self.X_scaled_mean = X_scaled_mean
        self.noise_var = noise_var
        X_norm_var = np.var(X_norm,axis=0)
        self.idx_sig = X_norm_var > 1
        self.idx_nonsig = (X_norm_var<=1) & (X_norm_var>0)
        if return_param == True:
            n_sig = sum(self.idx_sig)
            n_nonsig = sum(self.idx_nonsig)
            n_silent = X.shape[1] - n_sig - n_nonsig
            param = {
                '#significant genes':n_sig,
                '#non-significant genes':n_nonsig,
                '#silent genes':n_silent
            }
            return X_norm, param
        else:
            return X_norm
    
    def inv_noise_variance_stabilizing_normalization(
        self,
        X
    ):
        X_norm_inv_temp = X*np.sqrt(self.noise_var)+self.X_scaled_mean
        X_norm_inv = (X_norm_inv_temp.T*self.X_nUMI).T
        return X_norm_inv
    
    def fit(self,X):
        self.X = X
        self.idx_gene = np.sum(X,axis=0) > 0
        self.X_temp = X[:,self.idx_gene]

    def fit_transform(self,X):
        start = time.time()
        if self.verbose:
            print('start scRECODE')
        self.fit(X)
        param = {}
        X_norm,param_t = self.noise_variance_stabilizing_normalization(self.X_temp,return_param=True)
        param.update(param_t)
        recode = RECODE(return_param=True,param_estimate=False,acceleration=self.acceleration,acceleration_ell_max=self.acceleration_ell_max)
        X_norm_RECODE = recode.fit_transform(X_norm)
        X_scRECODE = np.zeros(X.shape,dtype=float)
        X_scRECODE[:,self.idx_gene] = self.inv_noise_variance_stabilizing_normalization(X_norm_RECODE)
        X_scRECODE = np.where(X_scRECODE>0,X_scRECODE,0)
        elapsed_time = time.time() - start
        param['#silent genes'] = sum(np.sum(X,axis=0)==0)
        param['ell'] = recode.ell
        param['elapsed_time'] = "{0}".format(np.round(elapsed_time,decimals=4
        )) + "[sec]"
        if self.verbose:
            print('end scRECODE')
            print('parameter:',param)
        if recode.ell == self.acceleration_ell_max:
            warnings.warn("Acceleration error: the ell value may not be optimal. Set 'acceleration=False' or larger acceleration_ell_max.\n"
            "Ex. X_new = screcode.scRECODE(acceleration=False).fit_transform(X)")
        self.X_scRECODE = X_scRECODE
        if self.return_param:
            return X_scRECODE, param
        else:
            return X_scRECODE
    
    def check_applicability(
            self,
          title='',
          figsize=(10,5),
          ps = 10,
          save = False,
          save_filename = 'check_applicability',
          save_format = 'png'
    ):
        X_scaled =(self.X_temp.T/np.sum(self.X_temp,axis=1)).T
        X_norm = self.noise_variance_stabilizing_normalization(self.X_temp)
        x,y = np.mean(X_scaled,axis=0),np.var(X_norm,axis=0)
        idx_nonsig, idx_sig = y <= 1, y > 1
        fig = plt.figure(figsize=figsize)
        spec = matplotlib.gridspec.GridSpec(ncols=2, nrows=1,width_ratios=[4, 1],wspace=0.)
        ax0 = fig.add_subplot(spec[0])
        ax0.scatter(x[idx_sig],y[idx_sig],color='b',s=ps,label='significant genes',zorder=2)
        ax0.scatter(x[idx_nonsig],y[idx_nonsig],color='r',s=ps,label='non-significant genes',zorder=3)
        ax0.axhline(1,color='gray',ls='--',lw=2,zorder=1)
        ax0.set_xscale('log')
        ax0.set_yscale('log')
        ax0.set_title(title,fontsize=14)
        ax0.set_xlabel('Mean of scaled data',fontsize=14)
        ax0.set_ylabel('Variance of normalized data',fontsize=14)
        ax0.legend(loc='upper left',borderaxespad=0,fontsize=14,markerscale=2).get_frame().set_alpha(0)
        ylim = ax0.set_ylim()
        ax1 = fig.add_subplot(spec[1])
        sns.kdeplot(y=np.log10(y), color='k',shade=True,ax=ax1)
        ax1.axhline(0,c='gray',ls='--',lw=2,zorder=1)
        ax1.axvline(0,c='k',ls='-',lw=1,zorder=1)
        ax1.set_ylim(np.log10(ax0.set_ylim()))
        ax1.tick_params(labelbottom=True,labelleft=False,bottom=True)
        ax1.set_xlabel('Density',fontsize=14)
        ax1.spines['right'].set_visible(False)
        ax1.spines['top'].set_visible(False)
        ax1.tick_params(left=False)
        if save:
            plt.savefig('%s.%s' % (save_filename,save_format))
        plt.show()
    
    def compare_mean_variance_log(
        self,
        title='',
        figsize=(15,5),
        ps = 10,
        size_factor='median',
        save = False,
        save_filename = 'compare_mean_variance_log',
        save_format = 'png'
    ):
        if size_factor=='median':
            size_factor = np.median(np.sum(self.X,axis=1))
            size_factor_scRECODE = np.median(np.sum(self.X_scRECODE,axis=1))
        elif size_factor=='mean':
            size_factor = np.mean(np.sum(self.X,axis=1))
            size_factor_scRECODE = np.mean(np.sum(self.X_scRECODE,axis=1))
        elif (type(size_factor) == int) | (type(size_factor) == float):
            size_factor_scRECODE = size_factor
        else:
            size_factor = np.median(np.sum(self.X,axis=1))
            size_factor_scRECODE = np.median(np.sum(self.X_scRECODE,axis=1))
        X_ss_log = np.log2(size_factor*(self.X[:,self.idx_gene].T/np.sum(self.X,axis=1)).T+1)
        X_scRECODE_ss_log = np.log2(size_factor_scRECODE*(self.X_scRECODE[:,self.idx_gene].T/np.sum(self.X_scRECODE,axis=1)).T+1)
        fig = plt.figure(figsize=figsize)
        ax0 = fig.add_subplot(1,2,1)
        x,y = np.mean(X_ss_log,axis=0),np.var(X_ss_log,axis=0)
        ax0.scatter(x[self.idx_sig],y[self.idx_sig],color='b',s=ps,label='significant genes',zorder=2)
        ax0.scatter(x[self.idx_nonsig],y[self.idx_nonsig],color='r',s=ps,label='non-significant genes',zorder=3)
        ax0.axhline(0,color='gray',ls='--',lw=2,zorder=1)
        ax0.set_xlabel('Mean of log-scaled data',fontsize=14)
        ax0.set_ylabel('Variance of log-scaled data',fontsize=14)
        ax0.set_title('Original',fontsize=14)
        ax0.legend(loc='upper left',borderaxespad=0,fontsize=14,markerscale=2).get_frame().set_alpha(0)
        ax1 = fig.add_subplot(1,2,2)
        x,y = np.mean(X_scRECODE_ss_log,axis=0),np.var(X_scRECODE_ss_log,axis=0)
        ax1.scatter(x[self.idx_sig],y[self.idx_sig],color='b',s=ps,label='significant genes',zorder=2)
        ax1.scatter(x[self.idx_nonsig],y[self.idx_nonsig],color='r',s=ps,label='non-significant genes',zorder=3)
        ax1.set_ylim(ax0.set_ylim())
        ax1.axhline(0,color='gray',ls='--',lw=2,zorder=1)
        ax1.set_xlabel('Mean of log-scaled data',fontsize=14)
        ax1.set_ylabel('Variance of log-scaled data',fontsize=14)
        ax1.set_title('scRECODE',fontsize=14)
        ax1.legend(loc='upper left',borderaxespad=0,fontsize=14,markerscale=2).get_frame().set_alpha(0)
        if save:
            plt.savefig('%s.%s' % (save_filename,save_format))
        plt.show()


def scRECODE_h5(h5_file, decimals=5):
    input_h5 = h5py.File(h5_file, 'r')
    X = scipy.sparse.csc_matrix((input_h5['matrix']['X'], input_h5['matrix']['indices'],
                                   input_h5['matrix']['indptr']), shape=input_h5['matrix']['shape']).toarray().T
    gene_list = [x.decode('ascii', 'ignore')
                 for x in input_h5['matrix']['features']['name']]
    cell_list = np.array([x.decode('ascii', 'ignore')
                         for x in input_h5['matrix']['barcodes']], dtype=object)
    X_scRECODE,param = scRECODE(return_param=True).fit_transform(X)
    X_scRECODE_csc = scipy.sparse.csc_matrix(
        np.round(X_scRECODE, decimals=decimals).T)
    outpur_h5 = '%s_scRECODE.h5' % (h5_file[:-3])
    with h5py.File(outpur_h5, 'w') as f:
        f.create_group('matrix')
        for key in input_h5['matrix'].keys():
            if key == 'X':
                f['matrix'].create_Xset(key, X=X_scRECODE_csc.X)
            elif key == 'indices':
                f['matrix'].create_Xset(key, X=X_scRECODE_csc.indices)
            elif key == 'indptr':
                f['matrix'].create_Xset(key, X=X_scRECODE_csc.indptr)
            elif key == 'shape':
                f['matrix'].create_Xset(key, X=X_scRECODE_csc.shape)
            elif type(input_h5['matrix'][key]) == h5py._hl.Xset.Xset:
                f['matrix'].create_Xset(key, X=input_h5['matrix'][key])
            else:
                f['matrix'].create_group(key)
                for key_sub in input_h5['matrix'][key].keys():
                    f['matrix'][key].create_Xset(
                        key_sub, X=input_h5['matrix'][key][key_sub])
        f['matrix'].create_Xset('scRECODE parameters', X=param)
