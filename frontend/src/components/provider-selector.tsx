"use client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { PROVIDER_PRESETS, type ProviderKind } from "@/lib/provider-config";

export function ProviderSelector({
  value,
  onChange,
}: {
  value: ProviderKind;
  onChange: (v: ProviderKind) => void;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
      {PROVIDER_PRESETS.map((p) => (
        <Button
          key={p.key}
          variant={value === p.key ? "default" : "outline"}
          className={cn(
            "h-auto justify-start py-3 px-3 text-left",
            value === p.key && "ring-2 ring-primary",
          )}
          onClick={() => onChange(p.key)}
          type="button"
        >
          <span className="text-sm font-medium leading-tight">{p.label}</span>
        </Button>
      ))}
    </div>
  );
}
