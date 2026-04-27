import type { Question } from "@/lib/types";
import { Card } from "@/components/ui/card";

export function LibraryStatsBar({ questions }: { questions: Question[] }) {
  const total = questions.length;
  const notPracticed = questions.filter((q) => q.status === "not_practiced").length;
  const practiced = questions.filter((q) => q.status === "practiced" || q.status === "improved").length;
  const needsRedo = questions.filter((q) => q.status === "needs_redo").length;
  return (
    <Card className="p-4">
      <div className="flex gap-6 text-sm">
        <div>
          <div className="text-2xl font-bold">{total}</div>
          <div className="text-muted-foreground">题库</div>
        </div>
        <div>
          <div className="text-2xl font-bold">{notPracticed}</div>
          <div className="text-muted-foreground">未练</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-green-600">{practiced}</div>
          <div className="text-muted-foreground">已练</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-destructive">{needsRedo}</div>
          <div className="text-muted-foreground">待重练</div>
        </div>
      </div>
    </Card>
  );
}
