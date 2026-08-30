# Containers: `FROM` and language runtimes

`FROM` in a Dockerfile does not lock you to one language. It only picks the **base image**: a starting filesystem that already has a runtime or toolchain.

The rest of a typical app Dockerfile is the same idea every time:

1. Set a working directory
2. Copy dependency files, then install or restore them
3. Copy the app
4. Expose a port
5. Start the process with `CMD` / `ENTRYPOINT`

This Journal API uses Python because the sample image was `python:3.11-slim` and the start command was Uvicorn. Node, C#, Java, or Go would work the same way with a different `FROM` and `CMD`.

## Python (this project)

Single stage: the image both installs packages and runs the app.

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Node.js

Still usually one stage. Swap Python/pip/Uvicorn for Node/npm/`node`.

```dockerfile
FROM node:20-slim

WORKDIR /app

COPY package*.json .
RUN npm ci --omit=dev

COPY . .

EXPOSE 8000

CMD ["node", "server.js"]
```

## C# (ASP.NET)

Multi-stage is common: **SDK** to compile, **runtime** to run the DLL.

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY *.csproj .
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /app .
EXPOSE 8000
ENV ASPNETCORE_URLS=http://0.0.0.0:8000
CMD ["dotnet", "JournalApi.dll"]
```

## Java

Same split: **JDK** to build a JAR, **JRE** to run it.

```dockerfile
FROM eclipse-temurin:21-jdk AS build
WORKDIR /app
COPY . .
RUN ./mvnw -q -DskipTests package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 8000
CMD ["java", "-jar", "app.jar"]
```

Gradle would use `./gradlew bootJar` instead of Maven. Spring Boot often defaults to port 8080; set 8000 in config or with `-Dserver.port=8000`.

## Go

Go compiles to one binary. The final image often has **no Go toolchain**.

```dockerfile
FROM golang:1.22 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /journal-api

FROM gcr.io/distroless/static
COPY --from=build /journal-api /journal-api
EXPOSE 8000
CMD ["/journal-api"]
```

`distroless` or `scratch` works when the binary is static (`CGO_ENABLED=0`).

## Comparison

| Language | Build image | Run image | Start command |
|----------|-------------|-----------|---------------|
| Python | `python:3.11-slim` | same | `uvicorn main:app ...` |
| Node | `node:20-slim` | same | `node server.js` |
| C# | `dotnet/sdk` | `dotnet/aspnet` | `dotnet JournalApi.dll` |
| Java | JDK (e.g. Temurin) | JRE | `java -jar app.jar` |
| Go | `golang` | `distroless` / `scratch` | `/journal-api` |

Python and Node often stay **one stage** because they interpret source at runtime. C#, Java, and Go usually use **multi-stage** builds: compile in a fat image, copy the artifact into a slim one.

Changing language means changing `FROM`, the install/build lines, and `CMD` — not the overall Docker model.

## Build and run locally

The Dockerfile is a recipe. `docker build` turns it into an **image**. `docker run` starts a **container** from that image (a running process with its own filesystem).

Docker Desktop must be running first. If the CLI says it cannot connect to the daemon (`unix:///Users/mac/.docker/run/docker.sock`), start Docker Desktop and wait until `docker info` works.

From `Project/Container`:

```bash
docker build -t journal-api .
```

`-t journal-api` names the image so you can run it without using a long image ID.

```bash
docker run -d --name journal-api -p 8000:8000 journal-api
```

- `-d` — run in the background
- `--name journal-api` — a stable name for logs/stop
- `-p 8000:8000` — host port 8000 → container port 8000 (`EXPOSE` only documents the port; `-p` actually publishes it)

Uvicorn binds `0.0.0.0:8000` inside the container so traffic from the host mapping can reach it. `127.0.0.1` inside the container would only accept connections from inside that container.

Check it is up:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

Interactive docs: http://localhost:8000/docs

### What was verified (30 Aug 2026)

Image `journal-api:latest` built from this folder. Container `journal-api` ran with `0.0.0.0:8000->8000/tcp`.

| Check | Result |
|--------|--------|
| `GET /health` | `{"status":"ok"}` |
| `GET /entries` (empty) | `[]` |
| `POST /entries` | Created an entry with an `id` |
| `GET /entries/{id}` | Same entry returned |
| `PATCH /entries/{id}` | Title updated |
| `DELETE /entries/{id}` | `204` |
| `GET` after delete | `404` `"Entry not found"` |

Entries are in memory, so they disappear when the container stops.

Logs:

```bash
docker logs journal-api
```

Stop and remove:

```bash
docker rm -f journal-api
```

