import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useSearchParams } from "react-router-dom";
import {
  FlaskConical, Bot, Moon, Sun, Plus, Trash2, Pencil, MessageSquare,
  ChevronsLeft, ChevronsRight, LayoutDashboard, BookOpen, Rocket,
  BrainCircuit, GitCompare, Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { useDarkMode } from "@/hooks/useDarkMode";
import { api, type SessionItem } from "@/lib/api";
import { useAgentStore } from "@/stores/agent";
import { ConnectionBanner } from "@/components/layout/ConnectionBanner";

const NAV = [
  { to: "/dashboard", icon: LayoutDashboard, key: "dashboard" as const },
  { to: "/agent",     icon: Bot,             key: "agent"     as const },
  { to: "/strategies",icon: BookOpen,        key: "strategies" as const },
  { to: "/execution", icon: Rocket,          key: "execution"  as const },
  { to: "/ml",        icon: BrainCircuit,    key: "mlCenter"   as const },
  { to: "/compare",   icon: GitCompare,      key: "compare"    as const },
  { to: "/settings",  icon: Settings,        key: "settings"   as const },
] as const;

type NavKey = typeof NAV[number]["key"];

export function Layout() {
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const { t } = useI18n();
  const { dark, toggle } = useDarkMode();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const sseStatus = useAgentStore(s => s.sseStatus);
  const sseRetryAttempt = useAgentStore(s => s.sseRetryAttempt);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("kairos-sidebar") === "collapsed"
  );

  const activeSessionId = searchParams.get("session");

  useEffect(() => {
    localStorage.setItem("kairos-sidebar", collapsed ? "collapsed" : "expanded");
  }, [collapsed]);

  const loadSessions = () => {
    api.listSessions()
      .then((list) => setSessions(Array.isArray(list) ? list : []))
      .catch(() => {})
      .finally(() => setSessionsLoading(false));
  };

  const isAgentPage = pathname.startsWith("/agent");
  useEffect(() => { loadSessions(); }, [isAgentPage, activeSessionId]);

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [renameTarget, setRenameTarget] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const deleteSession = async (sid: string) => {
    try {
      await api.deleteSession(sid);
      setSessions((prev) => prev.filter((s) => s.session_id !== sid));
    } catch { /* ignore */ }
    setDeleteTarget(null);
  };

  const renameSession = async (sid: string) => {
    if (!renameValue.trim()) { setRenameTarget(null); return; }
    try {
      await api.renameSession(sid, renameValue.trim());
      setSessions((prev) => prev.map((s) =>
        s.session_id === sid ? { ...s, title: renameValue.trim() } : s
      ));
    } catch { /* ignore */ }
    setRenameTarget(null);
  };

  const navLabel = (key: NavKey): string => t[key];

  return (
    <div className="flex h-screen bg-background">
      {/* ─── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className={cn(
        "border-r bg-card flex flex-col shrink-0 transition-all duration-200",
        collapsed ? "w-12" : "w-64"
      )}>
        {/* Brand */}
        <div className={cn("border-b", collapsed ? "p-2 flex justify-center" : "p-4")}>
          <Link
            to="/"
            className={cn(
              "flex items-center font-bold text-sm tracking-tight",
              collapsed ? "justify-center" : "gap-2"
            )}
          >
            <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center shrink-0">
              <FlaskConical className="h-4 w-4 text-primary-foreground" />
            </div>
            {!collapsed && (
              <div>
                <div className="text-sm font-bold leading-none">KAIROS</div>
                <div className="text-[10px] text-muted-foreground tracking-widest">QUANT v3.0</div>
              </div>
            )}
          </Link>
        </div>

        {/* Nav */}
        <nav className={cn("space-y-0.5", collapsed ? "p-1" : "p-2")}>
          {NAV.map(({ to, icon: Icon, key }) => {
            const isActive = to === "/dashboard"
              ? pathname === "/" || pathname.startsWith("/dashboard")
              : pathname.startsWith(to);
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  "flex items-center rounded-md text-sm transition-colors",
                  collapsed ? "justify-center p-2" : "gap-3 px-3 py-2",
                  isActive
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
                title={collapsed ? navLabel(key) : undefined}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && navLabel(key)}
              </Link>
            );
          })}
        </nav>

        {/* Sessions — only when expanded and on /agent */}
        {!collapsed && (
          <div className="flex-1 overflow-auto border-t mt-2 flex flex-col">
            <div className="flex items-center justify-between px-4 py-2">
              <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <MessageSquare className="h-3.5 w-3.5" />
                {t.sessions}
              </span>
              <Link
                to="/agent"
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                title={t.newChat}
              >
                <Plus className="h-3.5 w-3.5" />
              </Link>
            </div>

            <div className="px-2 pb-2 space-y-0.5 overflow-auto flex-1">
              {sessionsLoading ? (
                <div className="space-y-1.5 px-2 py-1">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-7 rounded-md bg-muted/50 animate-pulse" />
                  ))}
                </div>
              ) : sessions.length === 0 ? (
                <p className="px-3 py-2 text-xs text-muted-foreground/60">{t.noSessions}</p>
              ) : null}

              {sessions.map((s) => {
                const isActive = s.session_id === activeSessionId;
                const isDeleting = deleteTarget === s.session_id;
                const isRenaming = renameTarget === s.session_id;
                return (
                  <div key={s.session_id} className="group relative flex items-center">
                    {isRenaming ? (
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") renameSession(s.session_id);
                          if (e.key === "Escape") setRenameTarget(null);
                        }}
                        onBlur={() => renameSession(s.session_id)}
                        className="flex-1 min-w-0 pl-3 pr-2 py-1 rounded-md text-xs border border-primary bg-background outline-none"
                      />
                    ) : (
                      <Link
                        to={`/agent?session=${s.session_id}`}
                        className={cn(
                          "flex-1 min-w-0 pl-3 pr-14 py-1.5 rounded-md text-xs transition-colors truncate block border-l-2",
                          isActive
                            ? "border-l-primary bg-primary/10 text-primary font-medium"
                            : "border-l-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
                        )}
                        title={s.title || s.session_id}
                      >
                        <span className="flex items-center gap-1.5">
                          <span className={cn(
                            "h-1.5 w-1.5 rounded-full shrink-0",
                            s.status === "failed" ? "bg-danger" : isActive ? "bg-warning" : "bg-success/60"
                          )} />
                          {s.title || s.session_id.slice(0, 16)}
                        </span>
                      </Link>
                    )}
                    {!isRenaming && isDeleting ? (
                      <div className="absolute right-0.5 flex items-center gap-0.5">
                        <button
                          onClick={() => deleteSession(s.session_id)}
                          className="p-1 text-danger hover:bg-danger/10 rounded text-[10px] font-medium"
                        >
                          {t.confirmDelete}
                        </button>
                        <button
                          onClick={() => setDeleteTarget(null)}
                          className="p-1 text-muted-foreground hover:bg-muted rounded text-[10px]"
                        >
                          {t.cancelDelete}
                        </button>
                      </div>
                    ) : !isRenaming ? (
                      <div className="absolute right-1 opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setRenameTarget(s.session_id);
                            setRenameValue(s.title || "");
                          }}
                          className="p-1 text-muted-foreground hover:text-foreground rounded"
                          title={t.rename}
                        >
                          <Pencil className="h-3 w-3" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setDeleteTarget(s.session_id);
                          }}
                          className="p-1 text-muted-foreground hover:text-danger rounded"
                          title={t.deleteConfirm}
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {collapsed && <div className="flex-1" />}

        {/* Footer */}
        <div className={cn("border-t", collapsed ? "p-1 flex flex-col items-center gap-1" : "p-3 space-y-2")}>
          {collapsed ? (
            <>
              <button
                onClick={toggle}
                className="p-1.5 text-muted-foreground hover:text-foreground rounded transition-colors"
                title={dark ? t.lightMode : t.darkMode}
              >
                {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
              </button>
              <button
                onClick={() => setCollapsed(false)}
                className="p-1.5 text-muted-foreground hover:text-foreground rounded transition-colors"
                title="Mở rộng"
              >
                <ChevronsRight className="h-3.5 w-3.5" />
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <button
                  onClick={toggle}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
                  {dark ? t.lightMode : t.darkMode}
                </button>
                <button
                  onClick={() => setCollapsed(true)}
                  className="p-1 text-muted-foreground hover:text-foreground rounded transition-colors"
                  title="Thu gọn"
                >
                  <ChevronsLeft className="h-3.5 w-3.5" />
                </button>
              </div>
              <p className="text-xs text-muted-foreground/60">KAIROS v3.0 · Tiếng Việt</p>
            </>
          )}
        </div>
      </aside>

      {/* ─── Main ─────────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <ConnectionBanner status={sseStatus} retryAttempt={sseRetryAttempt} />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
