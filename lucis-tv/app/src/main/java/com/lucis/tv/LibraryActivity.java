package com.lucis.tv;

import android.app.*;
import android.os.*;
import android.content.*;
import android.graphics.Color;
import android.net.Uri;
import android.view.*;
import android.widget.*;
import androidx.documentfile.provider.DocumentFile;
import java.util.*;

public class LibraryActivity extends Activity {
    private static final int REQ_TREE=501;
    private GridLayout grid;
    private TextView status;
    private EditText search;
    private final ArrayList<Movie> allMovies=new ArrayList<>();

    static class Movie{String title;Uri uri;Movie(String t,Uri u){title=t;uri=u;}}

    @Override public void onCreate(Bundle b){super.onCreate(b);buildUi();loadSavedTree();}
    private TextView text(String s,int size){TextView t=new TextView(this);t.setText(s);t.setTextColor(Color.WHITE);t.setTextSize(size);t.setPadding(18,10,18,10);return t;}
    private Button button(String s){Button b=new Button(this);b.setText(s);b.setTextSize(18);b.setFocusable(true);b.setAllCaps(false);return b;}

    private void buildUi(){
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(Color.rgb(7,8,12));root.setPadding(34,24,34,24);
        TextView title=text("港片经典 · 本地影视库",30);title.setTypeface(null,1);root.addView(title);
        status=text("选择你的 U 盘 / 硬盘 / 本地电影目录。支持搜索、观看进度、自动续播、粤语优先。",14);status.setTextColor(Color.LTGRAY);root.addView(status);
        LinearLayout actions=new LinearLayout(this);actions.setOrientation(LinearLayout.HORIZONTAL);Button choose=button("选择电影文件夹");Button refresh=button("刷新");actions.addView(choose);actions.addView(refresh);root.addView(actions);
        search=new EditText(this);search.setHint("搜索片名");search.setTextColor(Color.WHITE);search.setHintTextColor(Color.GRAY);search.setSingleLine(true);root.addView(search);
        Button doSearch=button("搜索");root.addView(doSearch);
        ScrollView sc=new ScrollView(this);grid=new GridLayout(this);grid.setColumnCount(4);grid.setPadding(0,18,0,18);sc.addView(grid);root.addView(sc,new LinearLayout.LayoutParams(-1,0,1f));
        choose.setOnClickListener(v->chooseTree());refresh.setOnClickListener(v->loadSavedTree());doSearch.setOnClickListener(v->renderFiltered());setContentView(root);
    }

    private void chooseTree(){Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION|Intent.FLAG_GRANT_PREFIX_URI_PERMISSION);startActivityForResult(i,REQ_TREE);}
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){super.onActivityResult(requestCode,resultCode,data);if(requestCode!=REQ_TREE||resultCode!=RESULT_OK||data==null||data.getData()==null)return;Uri uri=data.getData();try{getContentResolver().takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(Exception ignored){}getSharedPreferences("lucis",MODE_PRIVATE).edit().putString("movie_tree",uri.toString()).apply();scan(uri);}
    private void loadSavedTree(){String s=getSharedPreferences("lucis",MODE_PRIVATE).getString("movie_tree","");if(s.isEmpty()){showEmpty("还没有影视库。\n\n按上方“选择电影文件夹”，选择你的 U 盘 / 硬盘电影目录。");return;}scan(Uri.parse(s));}

    private void scan(Uri treeUri){status.setText("正在扫描影视库…");grid.removeAllViews();new Thread(()->{ArrayList<Movie> out=new ArrayList<>();try{DocumentFile root=DocumentFile.fromTreeUri(this,treeUri);if(root!=null)walk(root,out,0);}catch(Exception ignored){}out.sort(Comparator.comparing(m->m.title.toLowerCase(Locale.ROOT)));runOnUiThread(()->{allMovies.clear();allMovies.addAll(out);renderFiltered();});}).start();}
    private void walk(DocumentFile dir,ArrayList<Movie> out,int depth){if(dir==null||depth>8||out.size()>=800)return;for(DocumentFile f:dir.listFiles()){if(out.size()>=800)break;if(f.isDirectory())walk(f,out,depth+1);else if(isVideo(f)){String n=f.getName()==null?"未命名影片":f.getName();out.add(new Movie(cleanTitle(n),f.getUri()));}}}
    private boolean isVideo(DocumentFile f){String m=f.getType();if(m!=null&&m.startsWith("video/"))return true;String n=f.getName();if(n==null)return false;n=n.toLowerCase(Locale.ROOT);return n.endsWith(".mkv")||n.endsWith(".mp4")||n.endsWith(".m4v")||n.endsWith(".avi")||n.endsWith(".mov")||n.endsWith(".ts")||n.endsWith(".webm");}
    private String cleanTitle(String n){int p=n.lastIndexOf('.');if(p>0)n=n.substring(0,p);return n.replace('.',' ').replace('_',' ').trim();}
    private String progressLabel(Uri uri){String key="progress_"+Integer.toHexString(uri.toString().hashCode());long pos=getSharedPreferences("lucis",MODE_PRIVATE).getLong(key,0L);long dur=getSharedPreferences("lucis",MODE_PRIVATE).getLong(key+"_duration",0L);if(pos<15_000||dur<=0)return"";int pct=(int)Math.max(1,Math.min(99,(pos*100L)/dur));return"\n继续观看 · "+pct+"%";}

    private void renderFiltered(){
        String q=search==null?"":search.getText().toString().trim().toLowerCase(Locale.ROOT);ArrayList<Movie> movies=new ArrayList<>();for(Movie m:allMovies)if(q.isEmpty()||m.title.toLowerCase(Locale.ROOT).contains(q))movies.add(m);
        grid.removeAllViews();status.setText("影视库 · "+movies.size()+" 部影片 · 粤语优先 · 自动续播");if(movies.isEmpty()){showEmpty(allMovies.isEmpty()?"没有找到常见视频文件。\n\n支持 MKV / MP4 / M4V / AVI / MOV / TS / WEBM。":"没有匹配的片名。");return;}
        for(Movie m:movies){Button card=button("🎬\n\n"+m.title+"\n\n粤语优先"+progressLabel(m.uri));card.setGravity(Gravity.CENTER);card.setMinHeight(250);card.setOnClickListener(v->play(m));GridLayout.LayoutParams lp=new GridLayout.LayoutParams();lp.width=0;lp.height=GridLayout.LayoutParams.WRAP_CONTENT;lp.columnSpec=GridLayout.spec(GridLayout.UNDEFINED,1f);lp.setMargins(8,8,8,8);grid.addView(card,lp);}if(grid.getChildCount()>0)grid.getChildAt(0).requestFocus();
    }

    private void showEmpty(String msg){grid.removeAllViews();TextView t=text(msg,17);t.setTextColor(Color.GRAY);grid.addView(t);}
    private void play(Movie m){Intent i=new Intent(this,PlayerActivity.class);i.putExtra("url",m.uri.toString());i.putExtra("name",m.title);startActivity(i);}
    @Override protected void onResume(){super.onResume();if(grid!=null&&grid.getChildCount()>0)loadSavedTree();}
}
