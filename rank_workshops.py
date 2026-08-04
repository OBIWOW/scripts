#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 26 11:13:51 2025

Rank ObiWoW workshops by ratings

@author: ekateria
"""

import pandas as pd

def get_ranks(rates):
    
    def get_avg(rates, col):
        avg=rates.groupby(['Workshop'])[col].mean().reset_index()
        avg=avg.sort_values(by=col, ascending=False)
        return round(avg,2)

    def get_comments(ws,col):
        comments=ws[[f'{col}_comment']].dropna()
        comments=comments[f'{col}_comment'].tolist()
        comments='; '.join(comments)
        return comments
    
    Ranks=pd.DataFrame()
    cols=['Usefullness','LectureLevel','PracticalSession','OverallImpression']
    for col in cols:
        rank=get_avg(rates,col)
        if len(Ranks)==0:
            Ranks=rank
        else:
            Ranks=Ranks.merge(rank, on='Workshop')
    
    num_resp=rates.groupby('Workshop')['Workshop'].count()
    num_resp=num_resp.rename('Count', inplace=True)
    num_resp=num_resp.reset_index()
    Ranks=Ranks.merge(num_resp, on='Workshop')
    
    Ranks=Ranks.set_index('Workshop')
    Ranks['AvgRate']=round(Ranks[cols].sum(axis=1)/len(cols),2)
    Ranks=Ranks.sort_values(by=['Count','AvgRate'], ascending=False)
    Ranks=Ranks.reset_index()
    
    ws_list=Ranks.loc[0:2,'Workshop'].tolist()
    ws_list=Ranks['Workshop'].tolist()
    for w in ws_list:
        ws=rates.loc[rates['Workshop']==w]
        for col in cols:
            comments=get_comments(ws,col)
            Ranks.loc[Ranks['Workshop']==w,f'{col}_comments']=comments
    
    Ranks=Ranks.sort_values(by=['Count','OverallImpression'],ascending=False)

    return Ranks

#Before loading the document, change the column names from questions asked to 'Usefulness', 'Usefullness_comment', 
#'LectureLevel', 'LectureLevel_comment', etc... Names are provided in 'cols' variable (line 29)

year='2025'
wdir='/Users/ekateria/Library/CloudStorage/OneDrive-UniversitetetiOslo/My_folder_CRCbiome_UiO/'
rates=pd.read_excel(f'{wdir}/ObiWoW/ObiWoW_ratings.xlsx', sheet_name=year)
rates=rates.dropna(subset=['Workshop'])

Ranks=get_ranks(rates)
Ranks.to_excel(f'{wdir}/ObiWoW/ObiWoW_ratings_summary_{year}.xlsx', index=False, sheet_name='Summary')

