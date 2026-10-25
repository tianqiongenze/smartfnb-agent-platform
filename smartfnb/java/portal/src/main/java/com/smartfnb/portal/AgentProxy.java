package com.smartfnb.portal;

import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.Map;
import java.util.concurrent.ExecutorService;

/** 智能体SSE代理(Undertow Servlet SseEmitter ← WebClient 流桥接) */
@RestController
@RequestMapping("/api/agent")
public class AgentProxy {

    private static final ParameterizedTypeReference<ServerSentEvent<String>> SSE_TYPE =
            new ParameterizedTypeReference<>() {};

    private final WebClient agent;
    private final ExecutorService pool = java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor();

    public AgentProxy(WebClient agentWebClient) { this.agent = agentWebClient; }

    @PostMapping(value = "/chat", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter chat(@RequestBody Map<String, Object> body) {
        SseEmitter emitter = new SseEmitter(120_000L);
        agent.post().uri("/api/agent/chat")
                .accept(MediaType.TEXT_EVENT_STREAM)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(body)
                .retrieve()
                .bodyToFlux(SSE_TYPE)
                .subscribe(
                        sse -> pool.submit(() -> {
                            try {
                                if (sse.event() != null) emitter.event().name(sse.event());
                                if (sse.id() != null) emitter.event().id(sse.id());
                                emitter.send(SseEmitter.event().data(sse.data() == null ? "" : sse.data()));
                            } catch (Exception ignored) { }
                        }),
                        emitter::completeWithError,
                        emitter::complete
                );
        return emitter;
    }
}
