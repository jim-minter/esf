all:

clean:
	find -name '*.pyc' -print0 | xargs -0 rm

.PHONY: all clean
