using System.Diagnostics;
using Microsoft.Web.WebView2.WinForms;

namespace VERTEX;

public class Form1 : Form
{
    private WebView2 webView;
    private Process? proc;

    public Form1()
    {
        Text = "VERTEX";
        Size = new Size(1280, 800);
        MinimumSize = new Size(900, 600);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(10, 10, 12);
    }

    protected override async void OnLoad(EventArgs e)
    {
        base.OnLoad(e);

        var dir = Path.GetDirectoryName(Application.ExecutablePath)!;
        var exe = Path.Combine(dir, "VERTEX.exe");
        if (!File.Exists(exe))
            exe = Path.Combine(dir, "..", "..", "..", "dist", "VERTEX.exe");
        if (!File.Exists(exe))
        { MessageBox.Show("VERTEX.exe not found"); return; }

        proc = Process.Start(new ProcessStartInfo
        {
            FileName = exe, UseShellExecute = true,
            WindowStyle = ProcessWindowStyle.Hidden, CreateNoWindow = true,
        });

        webView = new WebView2 { Dock = DockStyle.Fill };
        Controls.Add(webView);
        await webView.EnsureCoreWebView2Async();
        webView.CoreWebView2.Settings.AreDevToolsEnabled = false;
        await Task.Delay(2000);
        webView.CoreWebView2.Navigate("http://127.0.0.1:3000");
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        proc?.Kill(entireProcessTree: true);
        proc?.Dispose();
        base.OnFormClosing(e);
    }
}