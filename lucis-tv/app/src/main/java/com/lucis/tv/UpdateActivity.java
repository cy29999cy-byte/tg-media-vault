package com.lucis.tv;

import android.app.*;
import android.os.*;
import android.provider.Settings;
import android.content.*;
import android.graphics.Color;
import android.net.Uri;
import android.widget.*;
import org.json.JSONObject;
import java.io.*;
import java.net.*;

public class UpdateActivity extends Activity {
    private TextView status;
    private Button action;
    private String apkUrl="";
    private int remoteCode=0;
    private long downloadId=-1L;
    private BroadcastReceiver receiver;
    private static final int CURRENT_CODE=100;
    private static final String CURRENT_VERSION="1.0.0";
    private static final String META="https://raw.githubusercontent.com/cy29999cy-byte/tg-media-vault/lucis-tv-build/lucis-tv/update.json";

    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(50,40,50,40);root.setBackgroundColor(Color.rgb(9,10,13));
        TextView title=new TextView(this);title.setText("Lucis TV · 在线更新");title.setTextColor(Color.WHITE);title.setTextSize(30);title.setPadding(0,0,0,20);root.addView(title);
        status=new TextView(this);status.setTextColor(Color.LTGRAY);status.setTextSize(18);status.setText("当前版本："+CURRENT_VERSION+"\n\n正在检查更新…");root.addView(status);
        action=new Button(this);action.setText("检查更新");action.setTextSize(18);action.setFocusable(true);action.setEnabled(false);root.addView(action);
        action.setOnClickListener(v->{if(remoteCode>CURRENT_CODE&&!apkUrl.isEmpty())download();else check();});
        setContentView(root);check();
    }

    private void check(){
        action.setEnabled(false);status.setText("当前版本："+CURRENT_VERSION+"\n\n正在检查更新…");
        new Thread(()->{
            try{
                HttpURLConnection c=(HttpURLConnection)new URL(META).openConnection();c.setConnectTimeout(7000);c.setReadTimeout(7000);c.setUseCaches(false);
                BufferedReader r=new BufferedReader(new InputStreamReader(c.getInputStream()));StringBuilder sb=new StringBuilder();String line;while((line=r.readLine())!=null)sb.append(line);r.close();
                JSONObject o=new JSONObject(sb.toString());remoteCode=o.optInt("versionCode",0);apkUrl=o.optString("apkUrl","");String notes=o.optString("notes","");String version=o.optString("versionName","");
                runOnUiThread(()->{
                    if(remoteCode>CURRENT_CODE&&!apkUrl.isEmpty()){
                        status.setText("发现新版本 "+version+"\n\n"+notes+"\n\n按下方按钮即可直接在电视上下载更新，不需要再用 U 盘。");action.setText("下载并安装更新");action.setEnabled(true);
                    }else{status.setText("当前版本："+CURRENT_VERSION+"\n\n已经是最新版本。");action.setText("重新检查");action.setEnabled(true);}
                });
            }catch(Exception e){runOnUiThread(()->{status.setText("检查更新失败："+e.getMessage()+"\n\n网络恢复后可重试。");action.setText("重新检查");action.setEnabled(true);});}
        }).start();
    }

    private void download(){
        if(Build.VERSION.SDK_INT>=26&&!getPackageManager().canRequestPackageInstalls()){
            Intent s=new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,Uri.parse("package:"+getPackageName()));startActivity(s);Toast.makeText(this,"请先允许 Lucis TV 安装未知应用，然后返回再点一次更新",Toast.LENGTH_LONG).show();return;
        }
        try{
            DownloadManager dm=(DownloadManager)getSystemService(DOWNLOAD_SERVICE);DownloadManager.Request req=new DownloadManager.Request(Uri.parse(apkUrl));req.setTitle("Lucis TV 更新");req.setDescription("下载完成后自动打开安装界面");req.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);req.setMimeType("application/vnd.android.package-archive");
            downloadId=dm.enqueue(req);status.setText("正在下载更新…\n\n下载完成后会自动打开安装界面。");action.setEnabled(false);
            receiver=new BroadcastReceiver(){@Override public void onReceive(Context c,Intent i){if(DownloadManager.ACTION_DOWNLOAD_COMPLETE.equals(i.getAction())&&i.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID,-1)==downloadId)installDownloaded();}};
            registerReceiver(receiver,new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE));
        }catch(Exception e){status.setText("下载失败："+e.getMessage());action.setEnabled(true);}
    }

    private void installDownloaded(){
        try{DownloadManager dm=(DownloadManager)getSystemService(DOWNLOAD_SERVICE);Uri uri=dm.getUriForDownloadedFile(downloadId);if(uri==null)throw new IOException("下载文件不存在");Intent in=new Intent(Intent.ACTION_VIEW);in.setDataAndType(uri,"application/vnd.android.package-archive");in.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_ACTIVITY_NEW_TASK);startActivity(in);}catch(Exception e){status.setText("安装器打开失败："+e.getMessage()+"\n\n可在电视的下载目录手动打开 APK。");action.setEnabled(true);}
    }

    @Override protected void onDestroy(){super.onDestroy();if(receiver!=null){try{unregisterReceiver(receiver);}catch(Exception ignored){}receiver=null;}}
}
