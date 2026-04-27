"use client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import type { RoleType } from "@/lib/types";

const ROLES: { value: RoleType; label: string; tagline: string }[] = [
  { value: "pm", label: "产品", tagline: "PM / 产品运营 / AI 产品" },
  { value: "data", label: "数据", tagline: "数据分析 / DS / ML" },
  { value: "ai", label: "AI", tagline: "AI 产品 / AI 工程" },
  { value: "other", label: "其他岗位", tagline: "通用兜底" },
];

export function RoleSelector({
  value,
  onChange,
}: {
  value: RoleType | null;
  onChange: (v: RoleType) => void;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {ROLES.map((r) => (
        <Button
          key={r.value}
          variant={value === r.value ? "default" : "outline"}
          className={cn("h-auto flex flex-col items-start py-4 px-4", value === r.value && "ring-2 ring-primary")}
          onClick={() => onChange(r.value)}
        >
          <span className="font-semibold">{r.label}</span>
          <span className="text-xs text-muted-foreground mt-1">{r.tagline}</span>
        </Button>
      ))}
    </div>
  );
}
