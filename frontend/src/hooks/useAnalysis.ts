import { useState, useCallback } from 'react';
import { ShipMateReport, AgentStatus, AgentProgress } from '../types';

export interface AgentStreamEvent {
  type: 'agent_result';
  agent: 'repo_lens' | 'plan_forge' | 'guardrail' | 'testpilot';
  status: 'complete' | 'error';
  data?: any;
  error?: string;
}

export const useAnalysis = () => {
  const [report, setReport] = useState<ShipMateReport | null>(null);
  const [agentStatuses, setAgentStatuses] = useState<Record<string, AgentStatus>>({
    repo_lens: 'idle',
    plan_forge: 'idle',
    guardrail: 'idle',
    testpilot: 'idle',
  });
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(
    async (repoOwner: string, repoName: string, branch: string = 'main') => {
      setIsAnalyzing(true);
      setError(null);
      setAgentStatuses({
        repo_lens: 'running',
        plan_forge: 'running',
        guardrail: 'running',
        testpilot: 'running',
      });

      try {
        const response = await fetch(
          `/api/analyze?repo_owner=${encodeURIComponent(repoOwner)}&repo_name=${encodeURIComponent(repoName)}&branch=${encodeURIComponent(branch)}`,
          {
            method: 'POST',
            headers: {
              'Accept': 'text/event-stream',
            },
          }
        );

        if (!response.ok) {
          throw new Error(`Analysis failed: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('Failed to read response stream');
        }

        const decoder = new TextDecoder();
        let buffer = '';
        const agentOutputs: Record<string, any> = {};

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event: AgentStreamEvent = JSON.parse(line.slice(6));
                if (event.type === 'agent_result') {
                  // Update agent status
                  setAgentStatuses((prev) => ({
                    ...prev,
                    [event.agent]: event.status === 'complete' ? 'complete' : 'error',
                  }));

                  // Store agent output
                  if (event.status === 'complete' && event.data) {
                    agentOutputs[event.agent] = event.data;
                  }
                }
              } catch (e) {
                console.error('Failed to parse SSE event:', e);
              }
            }
          }
        }

        // All agents have completed; construct final report
        // (In a real implementation, you'd fetch or construct the full report)
        setIsAnalyzing(false);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMessage);
        setIsAnalyzing(false);
        setAgentStatuses({
          repo_lens: 'idle',
          plan_forge: 'idle',
          guardrail: 'idle',
          testpilot: 'idle',
        });
      }
    },
    []
  );

  return {
    report,
    agentStatuses,
    isAnalyzing,
    error,
    analyze,
  };
};
