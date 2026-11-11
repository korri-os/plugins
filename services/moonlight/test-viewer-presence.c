#define _GNU_SOURCE
#include "connection.h"
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

int main(void) {
  char directory[] = "/tmp/korri-presence-XXXXXX";
  assert(mkdtemp(directory));
  struct sockaddr_un address = {.sun_family = AF_UNIX};
  assert(snprintf(address.sun_path, sizeof(address.sun_path), "%s/notify", directory) > 0);
  int fd = socket(AF_UNIX, SOCK_DGRAM | SOCK_NONBLOCK, 0);
  assert(fd >= 0);
  assert(bind(fd, (struct sockaddr*)&address, sizeof(address)) == 0);
  assert(setenv("NOTIFY_SOCKET", address.sun_path, 1) == 0);
  connection_set_stream_size(1280, 720);
  assert(connection_callbacks.connectionStarted);
  connection_callbacks.connectionStarted();
  char data[256] = {0};
  ssize_t count = recv(fd, data, sizeof(data)-1, 0);
  assert(count > 0);
  assert(strncmp(data, "STATUS=korri-viewer-connected:", 29) == 0);
  assert(strstr(data, ":1280:720"));
  connection_callbacks.connectionTerminated(ML_ERROR_GRACEFUL_TERMINATION);
  memset(data, 0, sizeof(data));
  count = recv(fd, data, sizeof(data)-1, 0);
  assert(count > 0);
  assert(strcmp(data, "STATUS=korri-viewer-disconnected") == 0);
  unsetenv("NOTIFY_SOCKET");
  connection_callbacks.connectionStarted();
  assert(recv(fd, data, sizeof(data), 0) < 0);
  close(fd);
  unlink(address.sun_path);
  rmdir(directory);
  puts("viewer connection callbacks publish bounded native status");
}
