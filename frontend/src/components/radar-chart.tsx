"use client";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart as ReRadar,
  ResponsiveContainer,
} from "recharts";
import type { Rubric } from "@/lib/types";

export function RadarChart({
  rubric,
  scores,
}: {
  rubric: Rubric;
  scores: Record<string, number>;
}) {
  const data = rubric.dimensions.map((d) => ({
    dim: d.label,
    score: scores[d.key] ?? 0,
    fullMark: 3,
  }));
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ReRadar data={data}>
        <PolarGrid />
        <PolarAngleAxis dataKey="dim" />
        <PolarRadiusAxis angle={90} domain={[0, 3]} />
        <Radar name="得分" dataKey="score" fillOpacity={0.5} />
      </ReRadar>
    </ResponsiveContainer>
  );
}
