"use client";
import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Copy,
  Loader2,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { ProviderTestCategory, ProviderTestResult } from "@/lib/api";

export type ConnectionTestState =
  | { phase: "testing"; providerLabel: string; model: string; startedAt: number }
  | { phase: "result"; result: ProviderTestResult };

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  state: ConnectionTestState | null;
  /** When true and result.ok, auto-close after 2 seconds. Default true. */
  autoCloseOnSuccess?: boolean;
};

const CATEGORY_TITLE: Record<ProviderTestCategory, string> = {
  ok: "连接 OK",
  network: "网络不通",
  auth: "认证失败",
  rate_limit: "触发速率限制",
  json_format: "模型 JSON 输出不规范",
  unknown: "未知错误",
};

const CATEGORY_HINT: Record<ProviderTestCategory, string> = {
  ok: "",
  network:
    "请检查 base_url 是否正确，或 provider 服务可能临时不可用。",
  auth: "key 可能无效、过期或没有该 model 的访问权限。",
  rate_limit:
    "触发限流。可能是当前账户配额或并发限制，请稍后重试或检查 provider 控制台。",
  json_format:
    "该 model 在 JSON 输出上不可靠，agent 模块解析时容易失败。建议换 model 或换 provider 后重测。",
  unknown:
    "请截图本弹窗反馈：https://github.com/sereeein/MockInterview-Agent/issues",
};

function ElapsedCounter({ startedAt }: { startedAt: number }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 100);
    return () => clearInterval(id);
  }, []);
  return <span className="tabular-nums">{Math.max(0, now - startedAt)} ms</span>;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      type="button"
      size="xs"
      variant="ghost"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          // Clipboard may be unavailable (insecure context); silently no-op.
        }
      }}
    >
      <Copy />
      <span>{copied ? "已复制" : "复制"}</span>
    </Button>
  );
}

export function ConnectionTestDialog({
  open,
  onOpenChange,
  state,
  autoCloseOnSuccess = true,
}: Props) {
  // Auto-close on success
  useEffect(() => {
    if (!autoCloseOnSuccess) return;
    if (!open || !state) return;
    if (state.phase !== "result") return;
    if (!state.result.ok) return;
    const id = setTimeout(() => onOpenChange(false), 2000);
    return () => clearTimeout(id);
  }, [open, state, autoCloseOnSuccess, onOpenChange]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        {state?.phase === "testing" && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Loader2 className="size-4 animate-spin" />
                正在测试连接……
              </DialogTitle>
              <DialogDescription>
                正在调用 {state.providerLabel} 的 {state.model}
              </DialogDescription>
            </DialogHeader>
            <div className="text-sm text-muted-foreground">
              耗时：<ElapsedCounter startedAt={state.startedAt} />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                取消
              </Button>
            </DialogFooter>
          </>
        )}

        {state?.phase === "result" && state.result.ok && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="size-5" />
                {CATEGORY_TITLE.ok}
              </DialogTitle>
              <DialogDescription>
                耗时 <span className="tabular-nums">{state.result.elapsed_ms}</span> ms。
                配置可用，可以保存。
              </DialogDescription>
            </DialogHeader>
            {autoCloseOnSuccess && (
              <p className="text-xs text-muted-foreground">
                2 秒后自动关闭……
              </p>
            )}
          </>
        )}

        {state?.phase === "result" && !state.result.ok && (
          <ResultFailureBody
            result={state.result}
            onClose={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function ResultFailureBody({
  result,
  onClose,
}: {
  result: ProviderTestResult;
  onClose: () => void;
}) {
  const title = CATEGORY_TITLE[result.category];
  const hint = CATEGORY_HINT[result.category];
  const httpLine =
    result.http_status !== null && result.http_status !== undefined
      ? `HTTP ${result.http_status}`
      : "（无 HTTP 状态码）";
  const errorBlock = `${httpLine}\n${result.provider_message ?? "（无 provider 错误信息）"}`;

  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2 text-destructive">
          <AlertCircle className="size-5" />
          {title}
        </DialogTitle>
        <DialogDescription>{hint}</DialogDescription>
      </DialogHeader>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium text-muted-foreground">原始错误</p>
          <CopyButton text={errorBlock} />
        </div>
        <pre className="rounded border bg-muted/40 p-2 text-xs font-mono whitespace-pre-wrap break-all max-h-40 overflow-auto">
          {errorBlock}
        </pre>
      </div>

      {result.category === "json_format" && result.raw_response && (
        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground">
            模型实际返回（前 500 字符）
          </summary>
          <pre className="mt-2 rounded border bg-muted/40 p-2 font-mono whitespace-pre-wrap break-all max-h-40 overflow-auto">
            {result.raw_response}
          </pre>
        </details>
      )}

      <p className="text-xs text-muted-foreground">
        耗时 <span className="tabular-nums">{result.elapsed_ms}</span> ms
      </p>

      <DialogFooter>
        <Button variant="outline" onClick={onClose}>
          关闭
        </Button>
      </DialogFooter>
    </>
  );
}
