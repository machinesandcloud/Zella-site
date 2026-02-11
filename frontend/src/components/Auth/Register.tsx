import { useState } from "react";
import { Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import api from "../../services/api";

const Register = () => {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submit = async () => {
    await api.post("/api/auth/register", { username, email, password });
  };

  return (
    <Card elevation={0} sx={{ border: "1px solid var(--border)" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Register
        </Typography>
        <Stack spacing={2}>
          <TextField label="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
          <TextField label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button variant="contained" onClick={submit}>
            Create Account
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default Register;
