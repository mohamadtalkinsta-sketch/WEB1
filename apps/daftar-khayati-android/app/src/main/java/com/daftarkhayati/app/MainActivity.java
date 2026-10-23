package com.daftarkhayati.app;

import android.app.Activity;
import android.content.ClipData;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Parcelable;
import android.provider.MediaStore;
import android.view.View;
import android.view.Window;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.core.content.FileProvider;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends Activity {
    private static final int FILE_CHOOSER_REQUEST = 4054;
    private static final String APP_URL = "https://daftar-khayati.vercel.app/";

    private WebView webView;
    private ValueCallback<Uri[]> fileChooserCallback;
    private Uri cameraPhotoUri;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window window = getWindow();
        window.setStatusBarColor(Color.rgb(247, 245, 240));
        window.setNavigationBarColor(Color.rgb(247, 245, 240));
        window.getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(247, 245, 240));
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String host = uri.getHost();
                if (host != null && (host.equals("daftar-khayati.vercel.app") || host.endsWith(".vercel.app"))) {
                    return false;
                }
                if ("https".equalsIgnoreCase(uri.getScheme())) {
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, uri));
                    } catch (Exception ignored) { }
                }
                return true;
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(
                    WebView webView,
                    ValueCallback<Uri[]> filePathCallback,
                    FileChooserParams fileChooserParams) {
                if (fileChooserCallback != null) {
                    fileChooserCallback.onReceiveValue(null);
                }
                fileChooserCallback = filePathCallback;
                return openCameraOrGalleryChooser();
            }
        });

        setContentView(webView);
        if (savedInstanceState == null) {
            webView.loadUrl(APP_URL);
        } else {
            webView.restoreState(savedInstanceState);
        }
    }

    private boolean openCameraOrGalleryChooser() {
        Intent galleryIntent = new Intent(Intent.ACTION_GET_CONTENT);
        galleryIntent.addCategory(Intent.CATEGORY_OPENABLE);
        galleryIntent.setType("image/*");

        Intent chooser = Intent.createChooser(galleryIntent, "عکس بگیر یا از گالری انتخاب کن");
        List<Intent> cameraIntents = new ArrayList<>();

        Intent cameraIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        if (cameraIntent.resolveActivity(getPackageManager()) != null) {
            try {
                File photoFile = File.createTempFile("daftar_khayati_", ".jpg", getCacheDir());
                cameraPhotoUri = FileProvider.getUriForFile(
                        this, getPackageName() + ".fileprovider", photoFile);
                cameraIntent.putExtra(MediaStore.EXTRA_OUTPUT, cameraPhotoUri);
                cameraIntent.setClipData(ClipData.newUri(getContentResolver(), "camera-photo", cameraPhotoUri));
                cameraIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
                cameraIntents.add(cameraIntent);
            } catch (IOException | IllegalArgumentException ignored) {
                cameraPhotoUri = null;
            }
        }

        if (!cameraIntents.isEmpty()) {
            chooser.putExtra(Intent.EXTRA_INITIAL_INTENTS, cameraIntents.toArray(new Parcelable[0]));
        }

        try {
            startActivityForResult(chooser, FILE_CHOOSER_REQUEST);
            return true;
        } catch (Exception error) {
            if (fileChooserCallback != null) {
                fileChooserCallback.onReceiveValue(null);
                fileChooserCallback = null;
            }
            return false;
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != FILE_CHOOSER_REQUEST) return;

        Uri selectedUri = null;
        if (resultCode == RESULT_OK) {
            if (data != null && data.getData() != null) {
                selectedUri = data.getData();
            } else if (cameraPhotoUri != null) {
                selectedUri = cameraPhotoUri;
            }
        }

        if (fileChooserCallback != null) {
            fileChooserCallback.onReceiveValue(selectedUri == null ? null : new Uri[]{selectedUri});
            fileChooserCallback = null;
        }
        cameraPhotoUri = null;
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        if (webView != null) webView.saveState(outState);
        super.onSaveInstanceState(outState);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.stopLoading();
            webView.setWebChromeClient(null);
            webView.destroy();
            webView = null;
        }
        if (fileChooserCallback != null) {
            fileChooserCallback.onReceiveValue(null);
            fileChooserCallback = null;
        }
        super.onDestroy();
    }
}
