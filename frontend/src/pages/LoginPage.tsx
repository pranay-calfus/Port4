import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { forgotPassword } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { ErrorBanner, ErrorMessage, SuccessBanner } from "../components/ui/Feedback";
import { TextField } from "../components/ui/FormField";
import { Tabs } from "../components/ui/Tabs";

function ForgotPassword() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const res = await forgotPassword(email);
      setMessage(res.message);
    } catch (err) {
      setError(ErrorMessage(err));
    }
  }

  return (
    <div className="mt-4 border-t border-surface-border pt-4">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="text-sm text-ink-muted hover:text-ink"
      >
        {open ? "▾" : "▸"} Forgot password?
      </button>
      {open && (
        <form onSubmit={handleSubmit} className="mt-3 space-y-3">
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Button type="submit">Send reset link</Button>
          {message && <SuccessBanner message={message} />}
          {error && <ErrorBanner message={error} />}
        </form>
      )}
    </div>
  );
}

function CustomerLoginForm() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(ErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <form onSubmit={handleSubmit} className="space-y-4">
        <TextField
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <TextField
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <ErrorBanner message={error} />}
        <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
          Log In
        </Button>
      </form>
      <ForgotPassword />
    </Card>
  );
}

function CustomerRegisterForm() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register(name, email, password);
      navigate("/");
    } catch (err) {
      setError(ErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <form onSubmit={handleSubmit} className="space-y-4">
        <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <TextField
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <TextField
          label="Password"
          type="password"
          help="At least 8 characters"
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <ErrorBanner message={error} />}
        <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
          Create Account
        </Button>
      </form>
    </Card>
  );
}

function AdminLoginForm() {
  const { adminLogin } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await adminLogin(email, password);
      navigate("/admin");
    } catch (err) {
      setError(ErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <p className="mb-4 text-xs text-ink-muted">
        Super adminmust be configured from backend check: backend/create_admin.py.
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <TextField
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <TextField
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <ErrorBanner message={error} />}
        <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
          Log In
        </Button>
      </form>
    </Card>
  );
}

function ProductCxLoginForm() {
  const { productCxLogin } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await productCxLogin(email, password);
      navigate("/product-cx");
    } catch (err) {
      setError(ErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <form onSubmit={handleSubmit} className="space-y-4">
        <TextField
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <TextField
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <ErrorBanner message={error} />}
        <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
          Log In
        </Button>
      </form>
    </Card>
  );
}

export function LoginPage() {
  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <Tabs
        tabs={[
          {
            key: "customer",
            label: "Customer",
            content: (
              <Tabs
                tabs={[
                  { key: "login", label: "Log In", content: <CustomerLoginForm /> },
                  { key: "register", label: "Register", content: <CustomerRegisterForm /> },
                ]}
              />
            ),
          },
          { key: "admin", label: "Admin", content: <AdminLoginForm /> },
          { key: "product-cx", label: "Product & CX", content: <ProductCxLoginForm /> },
        ]}
      />
    </div>
  );
}
