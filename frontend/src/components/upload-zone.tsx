"use client";
import { useState } from "react";
import { cn } from "@/lib/utils";

export function UploadZone({ onFile }: { onFile: (file: File) => void }) {
  const [dragOver, setDragOver] = useState(false);

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const f = e.dataTransfer.files?.[0];
        if (f && f.type === "application/pdf") onFile(f);
      }}
      className={cn(
        "border-2 border-dashed rounded-lg p-10 text-center transition cursor-pointer",
        dragOver ? "border-primary bg-primary/5" : "border-border"
      )}
    >
      <input
        type="file"
        accept="application/pdf"
        id="resume-file"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
        }}
      />
      <label htmlFor="resume-file" className="cursor-pointer block">
        <p className="font-medium">拖入简历 PDF 或点击上传</p>
        <p className="text-xs text-muted-foreground mt-2">
          系统会智能解析项目 / 工作经历，反向挖出面试题
        </p>
      </label>
    </div>
  );
}
