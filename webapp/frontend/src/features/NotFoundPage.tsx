import { Scissors } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "@/components/common";
import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="mx-auto max-w-2xl p-6 pt-16">
      <EmptyState
        icon={Scissors}
        title="This page came unstitched"
        description="That page doesn't exist, or the project was moved to the trash."
        action={
          <Button asChild>
            <Link to="/">Back to projects</Link>
          </Button>
        }
      />
    </div>
  );
}
