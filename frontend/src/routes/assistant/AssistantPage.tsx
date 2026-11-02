import { PageHeader, Card } from '../../components/ui';
import { CopilotChat } from '../../components/copilot/CopilotChat';

export function AssistantPage() {
  return (
    <>
      <PageHeader
        title="Assistant"
        subtitle="Ask in plain words — it can search, tailor, track and prep for you. It never applies or messages anyone without you."
      />
      <Card className="p-0 overflow-hidden">
        <CopilotChat variant="page" />
      </Card>
    </>
  );
}
