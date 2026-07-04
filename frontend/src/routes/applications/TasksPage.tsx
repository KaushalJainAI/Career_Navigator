import { GoalsPanel } from './GoalsPanel';
import { TodosPanel } from './TodosPanel';

export function TasksPage() {
  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-black tracking-tight text-slate-950">Goals &amp; to-dos</h1>
        <p className="mt-1 text-sm font-semibold text-slate-500">
          Set targets for your search and keep every follow-up on track — all in one place.
        </p>
      </div>
      <GoalsPanel />
      <TodosPanel />
    </section>
  );
}
