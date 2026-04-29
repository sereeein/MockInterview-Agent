"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, Settings, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  findPreset,
  getStore,
  setActive,
  type ProviderConfigStore,
  type SavedConfig,
} from "@/lib/provider-config";

/** Header bar shown on every page (mounted from layout.tsx).
 *  v1.1: shows the active config + a dropdown to quick-switch between
 *  saved configs without going through /setup. */
export function ProviderHeader() {
  const pathname = usePathname();
  // Defer localStorage read to useEffect to avoid hydration mismatch
  const [store, setStoreState] = useState<ProviderConfigStore | null>(null);
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  function refresh() {
    setStoreState(getStore());
  }

  useEffect(() => {
    refresh();
    const onStorage = () => refresh();
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [pathname]);

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return;
    function onMouseDown(e: MouseEvent) {
      const target = e.target as Node | null;
      if (!target) return;
      if (panelRef.current?.contains(target)) return;
      if (triggerRef.current?.contains(target)) return;
      setOpen(false);
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onMouseDown);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onMouseDown);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open]);

  // Pre-mount: render null (matches SSR — avoids hydration mismatch)
  if (!store) return null;

  const active = store.configs.find((c) => c.id === store.activeId) ?? null;

  // No configs → minimal CTA strip pointing to setup
  if (store.configs.length === 0 || !active) {
    return (
      <div className="border-b bg-muted/40 px-4 py-2 text-xs flex justify-between items-center">
        <span className="text-muted-foreground">还没配置 Provider</span>
        <Link href="/setup" className="text-primary hover:underline">
          去 /setup 配置 →
        </Link>
      </div>
    );
  }

  function onPickConfig(cfg: SavedConfig) {
    if (cfg.lastTestStatus === "fail") {
      const ok = window.confirm(
        `「${cfg.name}」上次测试失败。仍要切换到这组配置吗？`,
      );
      if (!ok) {
        setOpen(false);
        return;
      }
    }
    setActive(cfg.id);
    refresh();
    setOpen(false);
  }

  const activePreset = findPreset(active.provider);
  const dotClass = (status: SavedConfig["lastTestStatus"]) =>
    status === "ok"
      ? "bg-emerald-500"
      : status === "fail"
        ? "bg-destructive"
        : "bg-muted-foreground/40";

  return (
    <div className="border-b bg-muted/40 px-4 py-1.5 text-xs flex justify-between items-center relative">
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">当前 Provider:</span>
        <button
          ref={triggerRef}
          type="button"
          onClick={() => setOpen((o) => !o)}
          className={cn(
            "inline-flex items-center gap-1.5 rounded px-2 py-1 transition-colors hover:bg-muted",
            open && "bg-muted",
          )}
          aria-haspopup="menu"
          aria-expanded={open}
        >
          <span className={cn("size-2 rounded-full", dotClass(active.lastTestStatus))} />
          <span className="font-medium text-foreground">{active.name}</span>
          <span className="text-muted-foreground">
            ({activePreset.label.split("（")[0]})
          </span>
          <ChevronDown
            className={cn("size-3 transition-transform", open && "rotate-180")}
          />
        </button>

        {open && (
          <div
            ref={panelRef}
            role="menu"
            className="absolute left-4 top-full mt-1 z-50 w-72 rounded-md border bg-popover shadow-lg ring-1 ring-foreground/10 p-1 text-sm"
          >
            <div className="px-2 py-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
              切换到其他配置
            </div>
            <div className="space-y-0.5 max-h-72 overflow-y-auto">
              {store.configs.map((cfg) => {
                const isActive = cfg.id === store.activeId;
                const isDefault = cfg.id === store.defaultId;
                const preset = findPreset(cfg.provider);
                return (
                  <button
                    key={cfg.id}
                    type="button"
                    onClick={() => !isActive && onPickConfig(cfg)}
                    className={cn(
                      "w-full flex items-center gap-2 px-2 py-1.5 rounded text-left transition-colors",
                      isActive
                        ? "bg-primary/10 cursor-default"
                        : "hover:bg-muted",
                    )}
                    disabled={isActive}
                  >
                    <span className={cn("size-2 rounded-full shrink-0", dotClass(cfg.lastTestStatus))} />
                    <span className="font-medium truncate flex-1">{cfg.name}</span>
                    {isDefault && (
                      <Star className="size-3 text-amber-500 fill-amber-500 shrink-0" />
                    )}
                    {isActive && (
                      <span className="text-[10px] font-medium text-primary shrink-0">
                        使用中
                      </span>
                    )}
                    <span className="text-[10px] text-muted-foreground shrink-0">
                      {preset.label.split("（")[0]}
                    </span>
                  </button>
                );
              })}
            </div>
            <div className="border-t mt-1 pt-1">
              <Link
                href="/setup"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-muted text-muted-foreground"
              >
                <Settings className="size-3.5" />
                管理配置 →
              </Link>
            </div>
          </div>
        )}
      </div>

      <Link
        href="/setup"
        className="text-primary hover:underline underline-offset-4"
      >
        设置
      </Link>
    </div>
  );
}
