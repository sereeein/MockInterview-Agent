"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { findPreset, getProviderConfig } from "@/lib/provider-config";

export function ProviderHeader() {
  const pathname = usePathname();
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    const refresh = () => {
      const cfg = getProviderConfig();
      setLabel(cfg ? findPreset(cfg.provider).label : null);
    };
    refresh();
    window.addEventListener("storage", refresh);
    return () => window.removeEventListener("storage", refresh);
  }, [pathname]);

  if (!label) return null;

  return (
    <div className="border-b bg-muted/40 px-4 py-2 text-xs flex justify-between items-center">
      <span className="text-muted-foreground">
        当前 Provider: <span className="font-medium text-foreground">{label}</span>
      </span>
      <Link href="/setup" className="text-primary hover:underline">
        切换 / 重设
      </Link>
    </div>
  );
}
