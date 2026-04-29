"use client";
import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

type SecretInputProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  /** Optional id passed to the underlying input (for label htmlFor). */
  id?: string;
};

export function SecretInput({
  value,
  onChange,
  placeholder,
  disabled,
  id,
}: SecretInputProps) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div className="relative w-full">
      <Input
        id={id}
        type={revealed ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="pr-9"
      />
      <Button
        type="button"
        size="icon-sm"
        variant="ghost"
        onClick={() => setRevealed((r) => !r)}
        disabled={disabled}
        className="absolute right-0.5 top-1/2 -translate-y-1/2"
        aria-label={revealed ? "隐藏" : "显示"}
      >
        {revealed ? <EyeOff /> : <Eye />}
      </Button>
    </div>
  );
}
