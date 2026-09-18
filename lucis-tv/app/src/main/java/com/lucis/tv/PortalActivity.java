package com.lucis.tv;

import android.app.*;
import android.os.*;
import android.graphics.Color;
import android.content.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.util.*;

public class PortalActivity extends Activity {
    private LinearLayout list;
    private TextView status;
    private EditText search;
    private final ArrayList<Entry> entries=new ArrayList<>();
    private String filter="all";
    private static final String CATALOG="https://raw.githubusercontent.com/cy29999cy-byte/tg-media-vault/lucis-tv-build/lucis-tv/catalog.json";

    static class Entry{
        String title,platform,category,url,note;
        Entry(String t,String p,String c,String u,String n){title=t;platform=p;category=c;url=u;note=n;}
    }

    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        filter=getIntent().getStringExtra("filter");
        if(filter==null||filter.isEmpty())filter="all";
        buildUi();
        seedFallback();
        render();
        refreshCatalog();
    }

    private TextView text(String s,int size){TextView t=new TextView(this);t.setText(s);t.setTextColor(Color.WHITE);t.setTextSize(size);t.setPadding(18,10,18,10);return t;}
    private Button button(String s){Button b=new Button(this);b.setText(s);b.setTextSize(18);b.setFocusable(true);b.setAllCaps(false);return b;}

    private void buildUi(){
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(Color.rgb(7,8,12));root.setPadding(34,24,34,24);
        TextView title=text(filter.equals("港片")?"经典港片 · 直播平台":"直播平台中心",30);title.setTypeface(null,1);root.addView(title);
        status=text("正在同步平台公开影视直播入口…",14);status.setTextColor(Color.LTGRAY);root.addView(status);

        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);
        Button all=button("全部");Button hk=button("港片 / 粤语");Button refresh=button("刷新入口");
        actions.addView(all);actions.addView(hk);actions.addView(refresh);root.addView(actions);

        search=new EditText(this);search.setHint("搜索：港片 / 粤语 / 虎牙 / 斗鱼");search.setSingleLine(true);search.setTextColor(Color.WHITE);search.setHintTextColor(Color.GRAY);root.addView(search);
        Button doSearch=button("搜索");root.addView(doSearch);

        ScrollView sc=new ScrollView(this);list=new LinearLayout(this);list.setOrientation(LinearLayout.VERTICAL);sc.addView(list);root.addView(sc,new LinearLayout.LayoutParams(-1,0,1f));
        all.setOnClickListener(v->{filter="all";render();});hk.setOnClickListener(v->{filter="港片";render();});refresh.setOnClickListener(v->refreshCatalog());doSearch.setOnClickListener(v->render());
        setContentView(root);
    }

    private void seedFallback(){
        entries.clear();
        entries.add(new Entry("虎牙 · 一起看影视直播","虎牙","港片直播","https://www.huya.com/g/2135","虎牙官方影视直播频道，平台实时更新直播房。"));
        entries.add(new Entry("斗鱼 · 一起看电影","斗鱼","港片直播","https://www.douyu.com/playlist/info/Qld2mlnKN","斗鱼官方电影播单入口。"));
        entries.add(new Entry("斗鱼 · 粤语电影 / 经典影片播单","斗鱼","粤语电影","https://www.douyu.com/playlist/all","斗鱼官方播单总览，可找到粤语电影、经典影片等。"));
        entries.add(new Entry("斗鱼 · 超清电影","斗鱼","电影直播","https://www.douyu.com/playlist/info/Aq8M1Xo9z","斗鱼官方超清电影播单。"));
        entries.add(new Entry("虎牙 · 影视频道总览","虎牙","直播平台","https://www.huya.com/g/seeTogether","虎牙官方“一起看”总入口。"));
        entries.add(new Entry("斗鱼 · 直播首页","斗鱼","直播平台","https://www.douyu.com/","斗鱼官方直播首页。"));
    }

    private void refreshCatalog(){
        status.setText("正在同步最新入口…");
        new Thread(()->{
            try{
                HttpURLConnection c=(HttpURLConnection)new URL(CATALOG+"?t="+System.currentTimeMillis()).openConnection();
                c.setConnectTimeout(7000);c.setReadTimeout(7000);c.setUseCaches(false);c.setRequestProperty("User-Agent","LucisTV/2.0");
                if(c.getResponseCode()<200||c.getResponseCode()>=300)throw new IOException("HTTP "+c.getResponseCode());
                BufferedReader r=new BufferedReader(new InputStreamReader(c.getInputStream()));StringBuilder sb=new StringBuilder();String line;while((line=r.readLine())!=null)sb.append(line);r.close();
                JSONArray arr=new JSONObject(sb.toString()).optJSONArray("entries");if(arr==null)throw new IOException("目录格式错误");
                ArrayList<Entry> next=new ArrayList<>();
                for(int i=0;i<arr.length();i++){JSONObject o=arr.optJSONObject(i);if(o==null)continue;String u=o.optString("url","");if(!u.startsWith("https://"))continue;next.add(new Entry(o.optString("title","直播入口"),o.optString("platform","平台"),o.optString("category","直播平台"),u,o.optString("note","")));}
                if(next.isEmpty())throw new IOException("目录为空");
                runOnUiThread(()->{entries.clear();entries.addAll(next);status.setText("已同步 · "+entries.size()+" 个官方平台入口");render();});
            }catch(Exception e){runOnUiThread(()->{status.setText("使用内置备用入口 · "+entries.size()+" 个");render();});}
        }).start();
    }

    private void render(){
        if(list==null)return;
        list.removeAllViews();
        String q=search==null?"":search.getText().toString().trim().toLowerCase(Locale.ROOT);
        int count=0;
        for(Entry e:entries){
            boolean hk=e.category.contains("港片")||e.category.contains("粤语")||e.note.contains("港片")||e.note.contains("粤语")||e.note.contains("周星驰")||e.note.contains("林正英");
            if(filter.equals("港片")&&!hk)continue;
            String hay=(e.title+" "+e.platform+" "+e.category+" "+e.note).toLowerCase(Locale.ROOT);
            if(!q.isEmpty()&&!hay.contains(q))continue;
            LinearLayout card=new LinearLayout(this);card.setOrientation(LinearLayout.VERTICAL);card.setPadding(8,8,8,8);
            Button open=button("▶  "+e.title+"   ["+e.category+"]");open.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);open.setOnClickListener(v->open(e));
            card.addView(open,new LinearLayout.LayoutParams(-1,-2));
            TextView note=text(e.note,13);note.setTextColor(Color.rgb(165,168,178));card.addView(note);
            list.addView(card);count++;
        }
        status.setText((filter.equals("港片")?"港片 / 粤语直播":"直播平台")+" · "+count+" 个入口 · 目录可在线更新");
        if(list.getChildCount()>0){View first=list.getChildAt(0);if(first instanceof ViewGroup&&((ViewGroup)first).getChildCount()>0)((ViewGroup)first).getChildAt(0).requestFocus();}
    }

    private void open(Entry e){
        Intent i=new Intent(this,WebViewActivity.class);i.putExtra("url",e.url);i.putExtra("title",e.title);startActivity(i);
    }
}
