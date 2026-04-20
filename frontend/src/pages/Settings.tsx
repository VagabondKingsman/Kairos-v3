import { useEffect, useState } from "react";
import { Save, AlertCircle, RefreshCw } from "lucide-react";

const API = "";

export function Settings() {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/config`);
      if (!res.ok) throw new Error("Không thể kết nối đến Backend A00");
      const data = await res.json();
      setConfig(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSuccessMsg(null);
    setError(null);
    try {
      const res = await fetch(`${API}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!res.ok) throw new Error("Lưu thất bại");
      setSuccessMsg("Đã lưu cấu hình thành công!");
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <RefreshCw className="h-6 w-6 animate-spin mr-2" /> Đang tải cấu hình...
      </div>
    );
  }

  if (error && !config) {
    return (
      <div className="flex-1 p-8 text-destructive flex items-center justify-center">
        <AlertCircle className="mr-2" /> {error}
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-background overflow-y-auto">
      <div className="border-b border-border/40 p-4 sticky top-0 bg-background/95 backdrop-blur z-10 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold">Cài Đặt Hệ Thống</h1>
          <p className="text-sm text-muted-foreground">Cấu hình danh mục giao dịch đa thị trường (A08)</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {saving ? "Đang lưu..." : "Lưu Cài Đặt"}
        </button>
      </div>

      {successMsg && (
        <div className="mx-4 mt-4 p-3 bg-emerald-500/15 border border-emerald-500/30 text-emerald-500 rounded-md flex items-center text-sm">
          ✅ {successMsg}
        </div>
      )}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-destructive/15 border border-destructive/30 text-destructive rounded-md flex items-center text-sm">
          <AlertCircle className="h-4 w-4 mr-2" /> {error}
        </div>
      )}

      <div className="p-4 grid gap-6 max-w-4xl">
        {/* 1. Crypto Config */}
        <div className="border border-border/50 rounded-lg p-5 bg-card">
          <h2 className="text-lg font-semibold mb-4 text-primary">Thị Trường Crypto</h2>
          <div className="grid gap-4">
            <div>
              <label className="text-sm text-muted-foreground block mb-1">Cặp Giao Dịch (cách nhau bằng dấu phẩy)</label>
              <input 
                type="text" 
                value={config?.markets?.crypto?.pairs?.join(", ")}
                onChange={(e) => {
                  const newPairs = e.target.value.split(",").map(s => s.trim()).filter(Boolean);
                  setConfig({
                    ...config,
                    markets: { ...config.markets, crypto: { ...config.markets.crypto, pairs: newPairs } }
                  });
                }}
                className="w-full bg-background border border-border rounded p-2 text-sm focus:border-primary outline-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-muted-foreground block mb-1">Đòn Bẩy (Leverage)</label>
                <input 
                  type="number" 
                  value={config?.markets?.crypto?.default_leverage || 1}
                  onChange={(e) => {
                    setConfig({
                      ...config,
                      markets: { ...config.markets, crypto: { ...config.markets.crypto, default_leverage: Number(e.target.value) } }
                    });
                  }}
                  className="w-full bg-background border border-border rounded p-2 text-sm outline-none"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground block mb-1">Phí Giao Dịch (Fee)</label>
                <input 
                  type="number" step="0.0001"
                  value={config?.markets?.crypto?.fee_rate || 0.001}
                  onChange={(e) => {
                    setConfig({
                      ...config,
                      markets: { ...config.markets, crypto: { ...config.markets.crypto, fee_rate: Number(e.target.value) } }
                    });
                  }}
                  className="w-full bg-background border border-border rounded p-2 text-sm outline-none"
                />
              </div>
            </div>
          </div>
        </div>

        {/* 2. Chứng khoán VN Config */}
        <div className="border border-border/50 rounded-lg p-5 bg-card">
          <h2 className="text-lg font-semibold mb-4 text-emerald-500">Chứng Khoán VNStock</h2>
          <div className="grid gap-4">
            <div>
              <label className="text-sm text-muted-foreground block mb-1">Mã Cổ Phiếu</label>
              <input 
                type="text" 
                value={config?.markets?.vnstock?.symbols?.join(", ")}
                onChange={(e) => {
                  const newSymbols = e.target.value.split(",").map(s => s.trim().toUpperCase()).filter(Boolean);
                  setConfig({
                    ...config,
                    markets: { ...config.markets, vnstock: { ...config.markets.vnstock, symbols: newSymbols } }
                  });
                }}
                className="w-full bg-background border border-border rounded p-2 text-sm focus:border-emerald-500 outline-none"
              />
            </div>
          </div>
        </div>

        {/* 3. Risk Management */}
        <div className="border border-border/50 rounded-lg p-5 bg-card">
          <h2 className="text-lg font-semibold mb-4 text-orange-500">Quản Trị Rủi Ro</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-sm text-muted-foreground block mb-1">Max Risk / Trade (%)</label>
              <input 
                type="number" step="0.01"
                value={config?.risk_management?.max_risk_per_trade_pct || 0}
                onChange={(e) => {
                  setConfig({
                    ...config,
                    risk_management: { ...config.risk_management, max_risk_per_trade_pct: Number(e.target.value) }
                  });
                }}
                className="w-full bg-background border border-border rounded p-2 text-sm outline-none"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground block mb-1">Max Drawdown (%)</label>
              <input 
                type="number" step="0.01"
                value={config?.risk_management?.max_daily_drawdown_pct || 0}
                onChange={(e) => {
                  setConfig({
                    ...config,
                    risk_management: { ...config.risk_management, max_daily_drawdown_pct: Number(e.target.value) }
                  });
                }}
                className="w-full bg-background border border-border rounded p-2 text-sm outline-none"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground block mb-1">Global Stop Loss (%)</label>
              <input 
                type="number" step="0.01"
                value={config?.risk_management?.global_stop_loss_pct || 0}
                onChange={(e) => {
                  setConfig({
                    ...config,
                    risk_management: { ...config.risk_management, global_stop_loss_pct: Number(e.target.value) }
                  });
                }}
                className="w-full bg-background border border-border rounded p-2 text-sm outline-none"
              />
            </div>
          </div>
        </div>
        
        {/* 4. A03 Settings */}
        <div className="border border-border/50 rounded-lg p-5 bg-card flex justify-between items-center">
          <div>
            <h2 className="text-lg font-semibold text-purple-500">Bộ Lọc A03 (Hội Đồng Đầu Tư)</h2>
            <p className="text-sm text-muted-foreground">Kích hoạt chế độ kiểm duyệt tín hiệu nghiêm ngặt bằng AI</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input 
              type="checkbox" 
              className="sr-only peer" 
              checked={config?.a03_filter_settings?.strict_mode || false}
              onChange={(e) => {
                setConfig({
                  ...config,
                  a03_filter_settings: { ...config.a03_filter_settings, strict_mode: e.target.checked }
                });
              }}
            />
            <div className="w-11 h-6 bg-muted peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-500"></div>
          </label>
        </div>

      </div>
    </div>
  );
}
