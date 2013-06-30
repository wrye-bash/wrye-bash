#
# Makefile

NAME := bait

TARGET32 := ${NAME}32.so
TARGET64 := ${NAME}64.so

${TARGET32}: ${NAME}.c
	gcc -m32 -shared -fPIC -o $@ $<
	if [ x"x86_64" == x"`uname -m`" ]; then \
	  gcc -shared -fPIC -o ${TARGET64} $<; \
	fi

clean:
	rm -f ${TARGET32} ${TARGET64}
