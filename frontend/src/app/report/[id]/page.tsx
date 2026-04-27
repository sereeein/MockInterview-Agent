"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { RadarChart } from "@/components/radar-chart";
import { TranscriptView } from "@/components/transcript-view";
import { getDrillReport } from "@/lib/api";
import type { SingleReport } from "@/lib/types";

const RATING = (score: number) => {
  if (score >= 11) return "优秀";
  if (score >= 9) return "良好";
  if (score >= 6) return "合格";
  return "需改进";
};

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const drillId = Number(id);
  const [report, setReport] = useState<SingleReport | null>(null);

  useEffect(() => {
    getDrillReport(drillId).then(setReport);
  }, [drillId]);

  if (!report) return <main className="container py-12">加载报告……</main>;

  return (
    <main className="container max-w-4xl mx-auto py-8 space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <Badge variant="secondary">{report.category}</Badge>
          <h1 className="text-xl font-bold mt-2">{report.question_text}</h1>
          <p className="text-xs text-muted-foreground mt-1">
            退出方式: {report.exit_type} · 追问 {report.followup_rounds} 轮
            {report.scenario_switch_count > 0 && ` · 场景切换 ${report.scenario_switch_count} 次`}
            {report.prompt_mode_count > 0 && ` · 求提示 ${report.prompt_mode_count} 次`}
          </p>
        </div>
        <Link href="/library">
          <Button variant="outline">返回题库</Button>
        </Link>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <h2 className="font-semibold">Rubric 评分</h2>
            <p className="text-2xl font-bold">
              {report.total_score} / 12 · {RATING(report.total_score)}
            </p>
          </CardHeader>
          <CardContent>
            <RadarChart rubric={report.rubric} scores={report.rubric_scores} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="font-semibold">改进建议</h2>
          </CardHeader>
          <CardContent>
            <ol className="list-decimal pl-5 space-y-2 text-sm">
              {report.improvement_suggestions.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>

      {report.exemplar_answer && (
        <Card>
          <CardHeader>
            <h2 className="font-semibold">范例答案（rubric 高分版本）</h2>
          </CardHeader>
          <CardContent className="text-sm whitespace-pre-wrap">{report.exemplar_answer}</CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <h2 className="font-semibold">完整对话</h2>
        </CardHeader>
        <CardContent>
          <TranscriptView transcript={report.transcript} />
        </CardContent>
      </Card>
    </main>
  );
}
