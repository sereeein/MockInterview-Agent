"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ScoreBarChart } from "@/components/score-bar-chart";
import { getMockReport } from "@/lib/api";
import type { MockReport } from "@/lib/types";

export default function MockReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const mockId = Number(id);
  const [report, setReport] = useState<MockReport | null>(null);

  useEffect(() => {
    getMockReport(mockId).then(setReport);
  }, [mockId]);

  if (!report) return <main className="container py-12">加载……</main>;

  const barData = report.drill_summaries.map((s) => ({
    label: `${s.category}·#${s.question_id}`,
    score: s.total_score,
  }));

  return (
    <main className="container max-w-4xl mx-auto py-8 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">整套面试报告</h1>
          <p className="text-muted-foreground mt-1">
            平均分 {report.total_avg_score.toFixed(1)} / 12
          </p>
        </div>
        <Link href="/library">
          <Button variant="outline">返回题库</Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">每题得分</h2>
        </CardHeader>
        <CardContent>
          <ScoreBarChart data={barData} />
        </CardContent>
      </Card>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <h2 className="font-semibold">高光时刻</h2>
          </CardHeader>
          <CardContent className="space-y-2">
            {report.highlights.length === 0 ? (
              <p className="text-sm text-muted-foreground">本场没有满分题——下次冲刺！</p>
            ) : (
              report.highlights.map((h) => (
                <div key={h.question_id} className="text-sm">
                  <Badge>{h.score}/12</Badge>
                  <span className="ml-2">{h.question_text}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="font-semibold">短板维度</h2>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {report.weaknesses.length === 0 ? (
              <p className="text-muted-foreground">无明显短板</p>
            ) : (
              report.weaknesses.map((w) => (
                <div key={w.dimension}>
                  <span className="font-medium">{w.dimension}</span>
                  <span className="text-muted-foreground"> · {w.avg.toFixed(1)} / 3 · 来自 {w.from_categories.join(", ")}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">下一步建议</h2>
        </CardHeader>
        <CardContent>
          <ul className="list-disc pl-5 space-y-1 text-sm">
            {report.next_steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">逐题汇总</h2>
        </CardHeader>
        <CardContent className="space-y-2">
          {report.drill_summaries.map((s) => (
            <Link key={s.drill_id} href={`/report/${s.drill_id}`} className="block">
              <div className="flex justify-between items-center border rounded p-3 hover:bg-muted text-sm">
                <span>
                  <Badge variant="secondary">{s.category}</Badge>{" "}
                  {s.question_text}
                </span>
                <span className="font-bold">{s.total_score} / 12</span>
              </div>
            </Link>
          ))}
        </CardContent>
      </Card>
    </main>
  );
}
