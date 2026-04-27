"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { LibraryStatsBar } from "@/components/library-stats-bar";
import { QuestionCard } from "@/components/question-card";
import { listQuestions } from "@/lib/api";
import type { Question } from "@/lib/types";

const CATS = ["T1", "T2", "T3", "T4", "T5"] as const;

function LibraryView() {
  const sp = useSearchParams();
  const router = useRouter();
  const sessionId = Number(sp.get("session"));
  const [questions, setQuestions] = useState<Question[]>([]);
  const [filter, setFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) return;
    listQuestions(sessionId).then((qs) => {
      setQuestions(qs);
      setLoading(false);
    });
  }, [sessionId]);

  const visible = filter ? questions.filter((q) => q.category === filter) : questions;

  return (
    <main className="container max-w-6xl mx-auto py-8 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">我的题库</h1>
        <Button onClick={() => router.push(`/mock?session=${sessionId}`)}>开始模拟面试</Button>
      </div>

      <LibraryStatsBar questions={questions} />

      <div className="flex gap-2">
        <Button variant={filter === null ? "default" : "outline"} size="sm" onClick={() => setFilter(null)}>
          全部
        </Button>
        {CATS.map((c) => (
          <Button
            key={c}
            variant={filter === c ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(c)}
          >
            {c}
          </Button>
        ))}
      </div>

      {loading ? (
        <p className="text-muted-foreground">加载题库……</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {visible.map((q) => (
            <QuestionCard key={q.id} q={q} />
          ))}
        </div>
      )}
    </main>
  );
}

export default function LibraryPage() {
  return (
    <Suspense fallback={<main className="container py-12">加载题库……</main>}>
      <LibraryView />
    </Suspense>
  );
}
