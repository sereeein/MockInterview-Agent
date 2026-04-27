"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RoleSelector } from "@/components/role-selector";
import { UploadZone } from "@/components/upload-zone";
import { generateQuestions, uploadResume } from "@/lib/api";
import type { RoleType } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [role, setRole] = useState<RoleType | null>(null);
  const [jd, setJD] = useState("");
  const [company, setCompany] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    if (!file || !role) {
      setError("请上传简历并选择岗位");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const rs = await uploadResume(file, role, jd || undefined, company || undefined);
      await generateQuestions(rs.id);
      router.push(`/library?session=${rs.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="container max-w-3xl mx-auto py-12 space-y-8">
      <div>
        <h1 className="text-3xl font-bold">MockInterview Agent</h1>
        <p className="mt-2 text-muted-foreground">
          垂直岗位 AI 面试演练 · 简历反向挖题 · 多轮追问
        </p>
      </div>

      <section className="space-y-3">
        <Label>1. 上传简历 (PDF)</Label>
        <UploadZone onFile={setFile} />
        {file && <p className="text-sm text-muted-foreground">已选择：{file.name}</p>}
      </section>

      <section className="space-y-3">
        <Label>2. 目标岗位</Label>
        <RoleSelector value={role} onChange={setRole} />
      </section>

      <section className="space-y-3">
        <Label htmlFor="jd">3. JD（可选，提供则出题更精准）</Label>
        <Textarea
          id="jd"
          rows={5}
          placeholder="粘贴 JD 文本……"
          value={jd}
          onChange={(e) => setJD(e.target.value)}
        />
      </section>

      <section className="space-y-3">
        <Label htmlFor="company">4. 公司名（可选）</Label>
        <Input
          id="company"
          placeholder="字节跳动 / Shopee / ……"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
        />
      </section>

      {error && <p className="text-destructive text-sm">{error}</p>}

      <Button size="lg" onClick={start} disabled={busy || !file || !role}>
        {busy ? "解析中…可能需要 30-60 秒" : "开始挖题"}
      </Button>
    </main>
  );
}
