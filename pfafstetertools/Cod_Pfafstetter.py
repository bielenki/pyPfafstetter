# -*- coding: utf-8 -*-
# Codificacao de Otto Pfafstetter
# Claudio Bielenki Junior
# Especialista em Geoprocessamento ANA
# Mar 2019

# importacao dos modulos
import os, sys, math
import pandas as pd
import pysal as ps
import numpy as np
from shutil import copyfile
import arcpy

def COC (pfafstetter):
    i=-1
    for cont in range(len(pfafstetter)):
        if int(pfafstetter[i]) % 2 == 0:
            cocursodag= pfafstetter[:len(pfafstetter)-cont]
            break
        i=i-1
    return (cocursodag)

def dbf2DF(dbfile): # Parametro arquivo dbf
         '''
            a funcao le o arquivo dbf e converte em Pandas Data Frame
            mantendo o nome dos atributos
         '''
         db = ps.open(dbfile) #Pysal para ler o DBF
         d = {col: db.by_col(col) for col in db.header} #Converte o dbf em dicionario
         pandasDF = pd.DataFrame(d) #Converte para Pandas DF
         db.close()   # fecha o arquivo dbf
         return pandasDF   # Retorna um data frame

def appendcol2dbf(dbf_in, dbf_out, col_name, col_spec, col_data,
                  replace=False):

    '''
        a funcao adiciona a um dbf um campo com os respectivos dados
    '''
    # abre o dbf original e cria um novo com o novo campo
    db= ps.open(dbf_in)
    db_new = ps.open(dbf_out, 'w')
    db_new.header = db.header
    db_new.header.append(col_name)
    db_new.field_spec = db.field_spec
    db_new.field_spec.append(col_spec)
    # adiciona ao dbf o dado original e o novo dado
    item = 0
    for rec in db:
        rec_new = rec
        rec_new.append(col_data[item])
        db_new.write(rec_new)
        item += 1
    # fecha os arquivos
    db_new.close()
    db.close()

    if replace is True:
        os.remove(dbf_in)
        os.rename(dbf_out, dbf_in)

def classif_rios(df):
    '''
        a funcao classifica uma selecao de trechos para o primeiro nivel
        a partir da identificacao do canal principal
    '''
    delta=0.9*df.Perimetro.min()
    teste=2
    max_acum=df.acc_down.max()
    FNODE=df.loc[df['acc_down']==max_acum]['fromnode'].max()
    principal=pd.DataFrame(columns=['area','id','dist','tnodeP','pfafstetter'])
    tributario=pd.DataFrame(columns=['area','id','dist','fnodeT','pfafstetter'])
    ind=df.loc[df['fromnode']==FNODE].index[0]
    x=df.loc[ind,'acc_down'].max()
    y=df.loc[ind,'rid'].max()
    z=df.loc[ind,'upDist'].max()-df.loc[ind,'Perimetro'].max()
    principal = principal.append({'area': x, 'id': y, 'dist': z, 'pfafstetter':'1'},ignore_index=True)

    i=0
    while teste==2:
        i=i+1
        teste=df.query('tonode=='+str(FNODE)).tonode.count()
        Maior_area=df.query('tonode=='+str(FNODE)).acc_down.max()
        Menor_area=df.query('tonode=='+str(FNODE)).acc_down.min()
        fnodeT=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).tonode.max()
        tnodeP=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).fromnode.max()
        ID_maior=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).rid.max()
        ID_menor=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Menor_area)).rid.max()
        dist_maior=(df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).upDist.max())-(df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).Perimetro.max())
        dist_menor=(df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Menor_area)).upDist.max())-(df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Menor_area)).Perimetro.max())
        principal = principal.append({'area': Maior_area, 'id': ID_maior, 'dist': dist_maior,'tnodeP': tnodeP,'pfafstetter': '999'},ignore_index=True)
        tributario = tributario.append({'area': Menor_area, 'id': ID_menor, 'dist': dist_menor,'fnodeT': fnodeT,'pfafstetter': '999'},ignore_index=True)
        FNODE=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).fromnode.max()
        if df.query('tonode=='+str(FNODE)).tonode.count() == 0 : break
    next
    copia=tributario.copy()
    copia=copia.sort_values('area',ascending=False)
    dados=pd.DataFrame(copia.reset_index(drop=True))
    if i<=3:
        areasSB=pd.DataFrame(dados.loc[0:i-1])
    else:
        areasSB=pd.DataFrame(dados.loc[0:3])
    areasSB=areasSB.sort_values('dist')
    Topfour=pd.DataFrame(areasSB.reset_index(drop=True))

    ultimo_interbac = str((Topfour.id.count()*2)+1)

    cont=1
    for rows in Topfour.pfafstetter:
        Topfour.loc[cont-1,'pfafstetter']=str(cont*2)
        cont=cont+1

    for index in Topfour.iterrows():
        distancia=(Topfour.loc[index[0],'dist'])-delta
        for index2, teste in principal.iterrows():
            if round(teste['dist'],3) < distancia and teste['pfafstetter']=='999' :
                print (teste['dist'])
                principal.loc[index2,'pfafstetter'] =  str(int(Topfour.loc[index[0],'pfafstetter'])-1)

    for index4, teste in principal.iterrows():
        if teste['pfafstetter']=='999' :
            principal.loc[index4,'pfafstetter'] = ultimo_interbac

    if i<=3:
        trib=dados.loc[i+1:]
    else:
        trib=dados.loc[4:]

    trib=trib.sort_values('dist')
    tributario=pd.DataFrame(trib.reset_index(drop=True))
    tributario.columns=['area','id','dist','fnodeT','pfafstetter']


    for index in Topfour.iterrows():
        dist_teste=(Topfour.loc[index[0],'dist'])-delta
        for index6, teste3 in tributario.iterrows():
            if round(teste3['dist'],3) < dist_teste and teste3['pfafstetter']=='999':
                tributario.loc[index6,'pfafstetter']= str(int(Topfour.loc[index[0],'pfafstetter'])-1)
            elif teste3['pfafstetter']=='999':
                break

    for index8, teste in tributario.iterrows():
        if teste['pfafstetter']=='999' :
            tributario.loc[index8,'pfafstetter'] = ultimo_interbac

    Topfour.columns=['area','id','dist','fnodeT','pfafstetter']
    frames = [Topfour,principal,tributario]
    framesConcat=pd.concat(frames)
    df_join=df.join(framesConcat.set_index('id'), on='rid',how='outer')
    df_join.drop_duplicates(subset='rid',keep='first',inplace=True)
    desconectados=[df_join.loc[df_join['pfafstetter'].isnull()].rid, df_join.loc[df_join['pfafstetter'].isnull()].tonode, df_join.loc[df_join['pfafstetter'].isnull()].upDist]
    list_desc=list(np.array(desconectados))
    Tlist=np.transpose(list_desc)
    dfTlist=pd.DataFrame(Tlist)
    dfTlist.sort_values(2,ascending=True, inplace=True)
    Tlist=np.array(dfTlist)
    cont=0

    for rows in Tlist:
        valor = df_join.loc[df_join['fromnode'] == Tlist[cont][1]]['pfafstetter'].max()
        df_join.set_value(df_join.loc[df_join['rid'] == Tlist[cont][0]]['pfafstetter'].index,'pfafstetter',str(int(valor)))
        cont=cont+1

    return (df_join)

def nascentes (df):
    Lfnode=list(df['fromnode'])
    Ltnode=list(df['tonode'])
    nasc=[item for item in Lfnode if item not in Ltnode]
    df_nasc=df[['rid','fromnode']]
    df_nasc['nascente']=0
    for item in nasc:
        df_nasc.set_value(df_nasc.loc[df_nasc['fromnode']==item].index,'nascente',1)
    return (df_nasc)


def canal_principal (df):
    max_acum=df.acc_down.max()
    FNODE=df.loc[df['acc_down']==max_acum]['fromnode'].max()
    teste=2
    canal=pd.DataFrame(columns=['area','id','tnodeP','canal'])
    ind=df.query('fromnode=='+str(FNODE)).index
    x=df.loc[ind,'acc_down'].max()
    y=df.loc[ind,'rid'].max()
    canal = canal.append({'area': x, 'id': y, 'canal':'1'},ignore_index=True)
    i=0
    while teste==2:
        i=i+1
        teste=df.query('tonode=='+str(FNODE)).tonode.count()
        Maior_area=df.query('tonode=='+str(FNODE)).acc_down.max()
        fnodeT=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).tonode.max()
        tnodeP=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).fromnode.max()
        ID_maior=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).rid.max()
        canal = canal.append({'area': Maior_area, 'id': ID_maior, 'tnodeP': tnodeP,'canal': 1},ignore_index=True)
        FNODE=df.query('tonode=='+str(FNODE)+'and acc_down=='+ str(Maior_area)).fromnode.max()
        if df.query('tonode=='+str(FNODE)).tonode.count() == 0 : break
    canalP=df.join(canal.set_index('id'), on='rid',how='outer')
    return (canalP)



pfaf_inicial=arcpy.GetParameterAsText(1)

rio = rio_shp.replace('shp','dbf')

df= dbf2DF(rio) # conversao de dbf para o pandas data frame



df.sort_values('upDist',ascending=True, inplace=True)

df_class1 = classif_rios(df)

df['pfaf']=df_class1['pfafstetter']

Todos_classificados=False

while Todos_classificados==False:

    Duplicados=df['pfaf'].duplicated()
    if True in list(Duplicados):
        for indexDuplicado, itemDuplicado in Duplicados.iteritems():
            if itemDuplicado == True:
                IndexDFpfaf=indexDuplicado
                break
        codpfaf=df.loc[IndexDFpfaf,'pfaf']
        sel_df=df[df['pfaf']==codpfaf]
        sel_df.sort_values('upDist',ascending=True, inplace=True)

        df_ClassN = classif_rios(sel_df)
        df_ClassN.sort_values('upDist',ascending=True, inplace=True)

        for indexDFjoin, itemDFjoin in df_ClassN.iterrows():
            var_rid = int(itemDFjoin.rid)
            pfaf1 = itemDFjoin.pfafstetter
            if type(pfaf1)==str:
                pfaf2=df.loc[df['rid']==var_rid]['pfaf']
                valor_pfaf = pfaf2.max()+pfaf1
                df.set_value(df.loc[df['rid'] == var_rid]['pfaf'].index,'pfaf',(valor_pfaf))
            if type(pfaf1)==float:
                if math.isnan(pfaf1):
                    valor_pfaf=df.loc[df['fromnode']==var_rid]['pfaf'].max()
                    df.set_value(df.loc[df['rid'] == var_rid]['pfaf'].index,'pfaf',(valor_pfaf))
                    break
                else:
                    pfaf2=df.loc[df['rid']==var_rid]['pfaf']
                    valor_pfaf = pfaf2.max()+pfaf1
                    df.set_value(df.loc[df['rid'] == var_rid]['pfaf'].index,'pfaf',(valor_pfaf))
    else:
        Todos_classificados=True
        break

for indexRow, rows in df.iterrows():
    pfaf3=rows['pfaf']
    pfaf_fim=pfaf_inicial+pfaf3
    df.set_value(indexRow,'pfaf',pfaf_fim)

canal = canal_principal(df)
na = nascentes(df)

df['cocurso']=''

for indexRow, rows in df.iterrows():
    pfafs=rows['pfaf']
    cocurso= COC(pfafs)
    df.set_value(indexRow,'cocurso',cocurso)

dbf_in = rio
dbf_out = rio.replace('.dbf','_copy.dbf')
col_name = 'Pfaf'
col_spec = ('C',15,0)
db = ps.open(dbf_in)
n = db.n_records
col_data = df.loc[df['pfaf'].notnull()]['pfaf']
db.close()
appendcol2dbf(dbf_in,dbf_out,col_name,col_spec,col_data,replace=True)

col_name = 'Canal'
col_spec = ('C',1,0)
db = ps.open(dbf_in)
n = db.n_records
col_data = canal['canal']
db.close()
appendcol2dbf(dbf_in,dbf_out,col_name,col_spec,col_data,replace=True)

col_name = 'Nascentes'
col_spec = ('C',1,0)
db = ps.open(dbf_in)
n = db.n_records
col_data = na['nascente']
db.close()
appendcol2dbf(dbf_in,dbf_out,col_name,col_spec,col_data,replace=True)

col_name = 'cocurso'
col_spec = ('C',15,0)
db = ps.open(dbf_in)
n = db.n_records
col_data = df['cocurso']
db.close()
appendcol2dbf(dbf_in,dbf_out,col_name,col_spec,col_data,replace=True)
