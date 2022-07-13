import streamlit as st
import altair as alt
import pandas as pd
import json
import tweepy
import MeCab

st.title('Twitter分析アプリ')
st.write('''
# このアプリはTwitter APIを使った分析アプリです。\n
ユーザーのタイムラインを様々な角度から分析します。
''')

option=st.sidebar.selectbox(
    'オプション',
    ['API認証とデータ取得','データ分析']

)

if option=='API認証とデータ取得':
    uploaded_file=st.file_uploader('認証JSONファイルをアップロード',type=['json'])
    if uploaded_file is not None:
        auth_info=json.load(uploaded_file)
        consumer_key,consumer_secret,access_token,access_token_secret,bearer_token=auth_info.values()

        client = tweepy.Client(bearer_token=bearer_token)
        st.write('認証が完了しました')

        username=st.text_input('ユーザー名を入力してください','03Imanyu')
        user_id=client.get_user(username=username).data.id

        st.write('### パラメータの設定')
        num_search_tweet=st.slider('検索件数',10,1000,50)

        if st.button('データ取得'):
            message=st.empty()
            message.write('取得中です')

            columns=['時間','ツイート本文','いいね','リツイート','ID']

            excludes=['retweets','replies']
            tweet_fields=['created_at','public_metrics']

            data=[]
            for tweet in tweepy.Paginator(client.get_users_tweets,user_id,exclude=excludes,tweet_fields=tweet_fields).flatten(limit=num_search_tweet):
                text,_id,public_metrics,created_at=tweet['text'],tweet['id'],tweet['public_metrics'],tweet['created_at']
                datum=[created_at,text,public_metrics['like_count'],public_metrics['retweet_count'],_id]
                data.append(datum)

            df=pd.DataFrame(data=data,columns=columns)
            csv=df.to_csv().encode('utf-8')

            message.success('CSVファイルの出力が完了しました') 
            st.download_button(
                label='CSVファイルをダウンロード',
                data=csv,
                file_name='twitter_data.csv',
                mime='text/csv'

            )
           
            st.dataframe(df)


if option=='データ分析':
     uploaded_file=st.file_uploader('分析用ファイルをアップロード',type=['csv'])
     if uploaded_file is not None:
        df=pd.read_csv(uploaded_file)
        hist=alt.Chart(df,title='いいね数の傾向').mark_bar().encode(
            alt.X('いいね',bin=alt.Bin(extent=[0,df['いいね'].max()],step=4),title='いいね数'),
            alt.Y('count()',title='回数'),
            tooltip=['count()']
         )

        st.altair_chart(hist,use_container_width=True)

        df['時間']=pd.to_datetime(df['時間'])
        df['時間']=df['時間'].dt.tz_convert('Asia/Tokyo')

        df['時刻']=df['時間'].dt.hour
        time_df=df[['いいね','時刻']]
        time_df=time_df.sort_values(by=['時刻'],ascending=True)
        groupd=time_df.groupby('時刻')

        mean=groupd.mean()
        mean.columns=['平均いいね数']

        size=groupd.size()
        base_time=pd.DataFrame([0]*24,index=list(range(0,24)))
        base_time.index.name='時刻'

        result=pd.concat([base_time,mean,size],axis=1).fillna(0)
        result.columns=['0','平均いいね数','ツイート数']
        result=result.drop('0',axis=1)
        result.reset_index(inplace=True)

        base=alt.Chart(result,title='時間ごとの傾向').encode(x='時刻:O')
        bar=base.mark_bar().encode(y='平均いいね数:Q',tooltip=['平均いいね数'])
        line=base.mark_line(color='blue').encode(y='ツイート数:Q',tooltip=['ツイート数'])

        st.altair_chart(bar+line,use_container_width=True)

        df.loc[df['いいね'] >= 100,'いいね評価']='A'
        df.loc[(df['いいね'] < 100) & (df['いいね'] >= 50),'いいね評価']='B'
        df.loc[(df['いいね'] < 50) & (df['いいね'] >= 30),'いいね評価']='C'
        df.loc[(df['いいね'] < 30) & (df['いいね'] >= 10),'いいね評価']='D'
        df.loc[df['いいね'] < 10,'いいね評価']='E'

        df['文字数']=df['ツイート本文'].str.len()
        grouped_fav=df.groupby('いいね評価')
        mean_word_df=grouped_fav.mean()[['文字数']]
        mean_word_df.reset_index(inplace=True)
        mean_word_df.columns=['等級','平均文字数']
        hist2=alt.Chart(mean_word_df,title='グレードと文字数の関係性').mark_bar().encode(
            x='等級',
            y='平均文字数',
            tooltip=['平均文字数']
        )

        st.altair_chart(hist2,use_container_width=True)

        wakati=MeCab.Tagger()

        grades=['A','B','C','D','E']
        for grade in grades:
            _df=df[df['いいね評価']==grade]
            num_tweet=len(_df)

            txt=' '.join(_df['ツイート本文'].to_list()).replace('https://t.co/','')
            parts=wakati.parse(txt)

            words=[]
            for part in parts.split('\n'):
                if '名詞' in part:
                    word=part.split('\t')[0]
                    words.append(word)

            c=Counter(words)
            cound_df=pd.DataFrame(c.most_common(30),columns=['単語','出現回数'])

            bar2=alt.Chart(cound_df,title=f'{grade}評価の頻出単語　ツイート数{num_tweet}').mark_bar().encode(
                x='出現回数:Q',
                y=alt.Y('単語:N',sort='-x')
            )

            text=bar2.mark_text(
                align='left',
                baseline='middle',
                dx=3
            ).encode(
                text='出現回数:Q'
            )

            st.altair_chart(bar2+text,use_container_width=True)





