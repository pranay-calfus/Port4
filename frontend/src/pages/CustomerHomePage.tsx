import { BulkTicketForm } from "../components/BulkTicketForm";
import { ChatBox } from "../components/ChatBox";
import { TicketList } from "../components/TicketList";
import { Tabs } from "../components/ui/Tabs";

export function CustomerHomePage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <Tabs
        tabs={[
          { key: "new", label: "New Ticket", content: <ChatBox /> },
          { key: "bulk", label: "Bulk Submit", content: <BulkTicketForm /> },
          { key: "mine", label: "My Tickets", content: <TicketList /> },
        ]}
      />
    </div>
  );
}
