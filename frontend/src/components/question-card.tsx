"use client";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import type { Question } from "@/lib/types";

const STATUS_LABEL: Record<Question["status"], string> = {
  not_practiced: "未练",
  practiced: "已练",
  needs_redo: "待重练",
  improved: "已改进",
  skipped: "已跳过",
};

const STATUS_VARIANT: Record<Question["status"], "default" | "secondary" | "destructive" | "outline"> = {
  not_practiced: "outline",
  practiced: "default",
  needs_redo: "destructive",
  improved: "default",
  skipped: "secondary",
};

export function QuestionCard({ q }: { q: Question }) {
  return (
    <Link href={`/drill/${q.id}`} className="block">
      <Card className="hover:border-primary transition cursor-pointer h-full">
        <CardHeader className="space-y-2">
          <div className="flex gap-2">
            <Badge variant="secondary">{q.category}</Badge>
            <Badge variant="outline">{q.difficulty}</Badge>
            <Badge variant={STATUS_VARIANT[q.status]}>{STATUS_LABEL[q.status]}</Badge>
          </div>
          <p className="font-medium leading-snug line-clamp-3">{q.text}</p>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground line-clamp-2">{q.source}</CardContent>
        <CardFooter className="text-xs text-muted-foreground flex justify-between">
          <span>最高分 {q.best_score ?? "—"} / 12</span>
          <span>{q.last_attempt_at ? new Date(q.last_attempt_at).toLocaleDateString() : "未练习"}</span>
        </CardFooter>
      </Card>
    </Link>
  );
}
